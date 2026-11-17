"""FastAPI service for the Urban Explorer AI content pipeline — 5 crews
(Discovery, Enrichment, Content, Hiker, Director) instead of one big crew,
so a user opening a brand-new city gets map pins fast instead of waiting
for everything to finish.

POST /kickoff        — legacy multi-city endpoint, called daily by
                        supabase/functions/crewai-trigger-refresh (pg_cron).
                        Loops the same per-city pipeline used by /ingest.
POST /ingest          — single-city endpoint for real-time use (e.g. the
                        app opening a brand-new city): Discovery runs first
                        and fast; Enrichment+Content launch together right
                        after (Content genuinely needs Enrichment's output,
                        so "parallel" here means launched together, not
                        zero-dependency — see _run_pipeline_for_city);
                        Hiker launches immediately, independently, only if
                        mode="hiker"; Director always runs last.
GET  /status/{city_id} — which crews have finished for a city (in-memory,
                        this-process-only) + live Supabase content counts.
GET  /                — admin/status page.
"""
import json
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import escape
from urllib.parse import quote

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from config import CREWAI_KICKOFF_TOKEN, supabase
from crew import ContentCrew, DirectorCrew, DiscoveryCrew, EnrichmentCrew, HikerCrew
from schemas import CityJob

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crewai-urban-explorer")

app = FastAPI(title="Urban Explorer AI — CrewAI content service")

MAX_LOG_ENTRIES = 30
CREWS = ("discovery", "enrichment", "content", "hiker", "director")

# Single-process in-memory state — fine for one Railway instance; if this
# ever scales to multiple instances, move this to a Supabase table instead.
run_state = {
    "status": "idle",  # idle | running | done | error
    "last_kickoff_at": None,
    "last_finished_at": None,
    "last_trigger": None,
    "cities_last_run": [],
    "log": [],  # list of {timestamp, message}
}
run_state_lock = threading.Lock()

# Per-city crew status, keyed by city name. Reset each time a pipeline run
# starts for that city; not persisted across restarts (see GET /status's
# docstring below for why that's an acceptable tradeoff here).
city_status: dict[str, dict] = {}
city_status_lock = threading.Lock()

# /ingest's real-time entry point used to spawn one raw threading.Thread()
# per request with no cap — fine for occasional real-time calls, but a
# burst of requests (e.g. pre-caching many cities) piles up threads that
# each live for minutes, and eventually the OS refuses to hand out more
# ("RuntimeError: can't start new thread"), confirmed in production. A
# bounded pool fixes this: at most MAX_CONCURRENT_INGESTS pipelines run at
# once: system-wide, everything else submitted waits in the executor's own
# queue instead of spawning anything or being dropped.
#
# That bound caps *concurrent* entry, but doesn't stop threads from piling
# up *cumulatively* over many sequential cities: CrewAI (and litellm,
# opentelemetry, requests' connection pools underneath it) spawn their own
# internal daemon threads during kickoff() that we have no handle to and
# that don't always exit promptly when kickoff() returns. Confirmed in
# production: a batch of 40 cities got through ~10 cleanly, then every
# subsequent city failed — 18 with an in-process "unhandled worker
# exception" (the OS finally refusing new threads mid-pipeline), then the
# remaining cities failing at the HTTP layer itself once the process-wide
# thread count was exhausted enough that even accepting a new request
# could fail.
#
# ProcessPoolExecutor would isolate each city's thread usage in its own OS
# process, which is the textbook fix — deliberately NOT used here though:
# city_status/run_state (this module's in-memory pipeline-progress state,
# read by GET /status and GET /) live in this process's memory and would
# silently stop updating from a worker in a different process; and this is
# a long-running FastAPI process with its own threads and an already-
# instantiated Supabase/httpx client (open connections/thread state), so
# fork()-ing a worker off of it while it's live is a well-known source of
# hangs and corrupted connections. Falling back to the documented
# alternative instead: reap what's reapable and give the OS a moment to
# reclaim the rest between cities (see _reap_leaked_threads below).
MAX_CONCURRENT_INGESTS = 2
_ingest_executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_INGESTS, thread_name_prefix="ingest")
_ingest_lock = threading.Lock()
_ingest_in_flight = 0

# Seconds to pause after each city (inside the try/finally below) before a
# pool worker — or the sequential /kickoff loop — picks up the next one,
# giving the OS a window to actually reclaim thread resources rather than
# racing straight into the next city's kickoff() while leaked threads from
# the previous one are still unwinding.
POST_CITY_COOLDOWN_SECONDS = 3
# Bounded per-thread join — these are threads we don't own (CrewAI's own
# internals), so a thread still alive after this long is treated as
# genuinely leaked for this city rather than blocked waiting to reap it.
THREAD_REAP_JOIN_TIMEOUT_SECONDS = 0.5


def _reap_leaked_threads(city: str) -> None:
    """Best-effort cleanup for the thread leak described above. This can't
    stop CrewAI/litellm/etc. from spawning threads we don't control, and it
    can't force a genuinely stuck thread to exit — daemon threads die with
    the process regardless. What it does do: give any daemon thread that's
    already finished (or finishes within the short join window) a chance
    to be reaped by the interpreter *now*, right after this city, instead
    of sitting alive until the process happens to garbage-collect it —
    and log how many are still alive afterward, so a growing count is
    visible in Railway logs instead of silently building up until the next
    "can't start new thread" crash.
    """
    current = threading.current_thread()
    candidates = [
        t for t in threading.enumerate()
        if t is not current and t is not threading.main_thread() and t.daemon
    ]
    for t in candidates:
        t.join(timeout=THREAD_REAP_JOIN_TIMEOUT_SECONDS)
    still_alive = sum(1 for t in candidates if t.is_alive())
    _log(f"[{city}] thread reap: {len(candidates)} daemon thread(s) seen, {still_alive} still alive")

# city_cache statuses that mean "don't start another pipeline run for this
# city" — see _check_city_cache_gate(). 'pending' is deliberately NOT
# blocking: it only means "claimed but not yet actually started" (see that
# function's docstring for the resulting race window).
_CITY_CACHE_BLOCKING_STATUSES = {"discovery", "enrichment", "content", "complete"}


def _log(message: str) -> None:
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "message": message}
    logger.info(message)
    with run_state_lock:
        run_state["log"].insert(0, entry)
        run_state["log"] = run_state["log"][:MAX_LOG_ENTRIES]


def _set_city_status(city: str, crew: str, status: str) -> None:
    with city_status_lock:
        city_status.setdefault(city, {c: "pending" for c in CREWS})
        city_status[city][crew] = status
        city_status[city]["updated_at"] = datetime.now(timezone.utc).isoformat()
    _log(f"[{city}] {crew}: {status}")


def _set_city_cache_status(city: str, status: str, **extra) -> None:
    """Persists a status transition to Supabase's city_cache table — unlike
    city_status above (in-memory, this-process-only), this is what the
    /ingest and /kickoff idempotency gate actually reads, and it survives a
    restart. Upsert (not a plain update) so this is safe to call even if
    the row doesn't exist yet for some reason — an update would silently
    no-op on a missing row instead of creating it. Best-effort: a Supabase
    hiccup here shouldn't take down a pipeline run that's otherwise
    progressing fine, so this only logs.
    """
    payload = {"city_name": city, "status": status, **extra}
    try:
        supabase.table("city_cache").upsert(payload, on_conflict="city_name").execute()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to update city_cache status for %s -> %s", city, status)


def _count_table_rows(table: str, city: str) -> int:
    """Live COUNT(*) for one of the content tables, scoped to a city — used
    both for the Discovery-skip check and for recording poi_count/
    event_count/business_count into city_cache."""
    try:
        res = supabase.table(table).select("id", count="exact").eq("city", city).execute()
        return res.count or 0
    except Exception:  # noqa: BLE001
        logger.exception("Failed to count %s for %s", table, city)
        return 0


def _parse_json_list(raw: str) -> list[dict]:
    """Saca la lista JSON de la respuesta de un agente (con o sin ```json)."""
    if not raw:
        return []
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(raw).strip())
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end <= start:
        return []
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        return []
    return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else []


def _ingest_direct(job: CityJob, kind: str, raw: str) -> str:
    """Guarda directamente lo que encontraron los buscadores (datos reales de
    OpenStreetMap / Wikipedia), sin depender de que el Director lo reenvíe.
    El Director después solo mejora textos de lo que ya está guardado."""
    from config import VALID_CATEGORIES
    from tools.supabase_ingest import SupabaseIngestTool

    items = []
    for it in _parse_json_list(raw):
        if it.get("category") not in VALID_CATEGORIES:
            continue
        it["city"] = job.city
        if job.country and not it.get("country"):
            it["country"] = job.country
        items.append(it)
    if not items:
        return f"[{job.city}] {kind}: nada que guardar"
    return SupabaseIngestTool()._run(kind, items, job.city)


def _fetch_existing_content_as_discovery_output(city: str) -> dict:
    """Builds a DiscoveryCrew-shaped output dict from what's already in
    Supabase for this city — used when Discovery (and Enrichment) are
    skipped because poi-discovery already populated it, so ContentCrew's
    Redactor task still gets real material to work from (see
    tasks/content/redactor_contenido.py, which just dumps whatever keys/
    values it's given into its prompt — the exact shape doesn't matter,
    only that it's genuine data, not fabricated).
    """
    output: dict[str, str] = {}
    for table, key in (("points_of_interest", "pois"), ("events", "events"), ("businesses", "businesses")):
        try:
            res = supabase.table(table).select("*").eq("city", city).execute()
            output[key] = json.dumps(res.data or [], default=str)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to fetch existing %s for %s", table, city)
            output[key] = "[]"
    return output


def _fetch_wikipedia_summary_and_cache(city: str) -> None:
    """Best-effort, non-blocking Wikipedia summary fetch — fired right when
    /ingest accepts a city, independent of (and much faster than) the
    CrewAI pipeline, so the app's loading screen has real content to show
    within a second or two instead of waiting on agents. Never raises: a
    miss (no matching English Wikipedia article, network hiccup, etc.)
    just means city_cache's wikipedia_* fields stay empty, which the
    client already needs to handle for any city without a match.
    """
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(city)}"
        resp = httpx.get(
            url, timeout=5.0,
            headers={"User-Agent": "UrbanExplorerApp/1.0 (contact@urbanexplorer.app)"},
        )
        if resp.status_code != 200:
            return
        data = resp.json()
        extract = data.get("extract")
        thumbnail_url = (data.get("thumbnail") or {}).get("source")
        if not extract and not thumbnail_url:
            return
        payload = {"city_name": city}
        if extract:
            payload["wikipedia_summary"] = extract
        if thumbnail_url:
            payload["wikipedia_image_url"] = thumbnail_url
        supabase.table("city_cache").upsert(payload, on_conflict="city_name").execute()
        _log(f"[{city}] Wikipedia summary cached")
    except Exception:  # noqa: BLE001
        logger.exception("Wikipedia summary fetch failed for %s", city)


def _check_city_cache_gate(city: str, country: str | None = None) -> tuple[bool, str | None]:
    """Idempotency gate for /ingest and /kickoff — one Supabase read (and,
    when allowing the request through, one write) before any pipeline work
    starts. Zero LLM calls.

    Returns (allowed, blocking_status):
      - allowed=False, blocking_status=<'discovery'|'enrichment'|'content'
        |'complete'> — a pipeline for this city is already in flight or
        already finished; caller should reject with 409.
      - allowed=True, blocking_status=None — caller may proceed. This
        claims the row (inserts a fresh 'pending' one, or resets an
        'error' row back to 'pending') so a later _set_city_cache_status
        call always has a row to update.

    Known race window: between this claim and _run_pipeline_for_city
    actually marking the row 'discovery' (its very first step), the row
    sits at 'pending' — which this gate does not block on — so a second
    concurrent request for the very same city arriving in that window
    would also pass through. That window is normally sub-second when a
    pool worker is free. Closing it fully needs a conditional DB-level
    upsert (e.g. "UPDATE ... WHERE status NOT IN (...)" or a Postgres
    function); not attempted here since this pass is meant to be a cheap,
    zero-LLM-cost hardening step, not a full concurrency rewrite.
    """
    try:
        res = supabase.table("city_cache").select("status").eq("city_name", city).execute()
        rows = res.data or []
        existing_status = rows[0]["status"] if rows else None
    except Exception:  # noqa: BLE001
        logger.exception("city_cache lookup failed for %s — allowing request through", city)
        existing_status = None

    if existing_status in _CITY_CACHE_BLOCKING_STATUSES:
        return False, existing_status

    now = datetime.now(timezone.utc).isoformat()
    try:
        if existing_status == "error":
            supabase.table("city_cache").update({
                "status": "pending", "error_message": None, "triggered_at": now,
            }).eq("city_name", city).execute()
        elif existing_status is None:
            supabase.table("city_cache").insert({
                "city_name": city, "country": country, "status": "pending", "triggered_at": now,
            }).execute()
        # existing_status == "pending" already: nothing to claim/reset.
    except Exception:  # noqa: BLE001
        logger.exception("Failed to claim city_cache row for %s", city)

    return True, None


def _finalize_city_cache(result: dict) -> None:
    """Writes the final city_cache status once a pipeline run has finished
    — shared by /ingest (via the thread pool) and /kickoff (sequential
    loop), so a city claimed by either entry point always gets un-stuck
    from 'discovery'/'enrichment'/'content' instead of being permanently
    (and incorrectly) treated as still in flight.
    """
    city = result["city"]
    if result["status"] == "error":
        message = "; ".join(result.get("errors", [])) or "unknown error"
        _set_city_cache_status(city, "error", error_message=message[:2000])
    else:
        _set_city_cache_status(
            city, "complete",
            completed_at=datetime.now(timezone.utc).isoformat(),
            poi_count=_count_table_rows("points_of_interest", city),
            event_count=_count_table_rows("events", city),
            business_count=_count_table_rows("businesses", city),
            error_message=None,
        )


def _run_pipeline_for_city(job: CityJob, want_hiker: bool) -> dict:
    """Discovery -> (Enrichment then Content, launched together) plus
    Hiker (independent, launched immediately if requested) -> Director.

    "Enrichment and Content in parallel" is implemented as: both start
    together right after Discovery, but Content's own thread body waits
    for Enrichment to actually finish before building its first task —
    Content's Redactor genuinely needs Enrichment's richer descriptions/
    history/hours/prices as input (that's the whole point of Enrichment
    existing), so running them with zero dependency between them would
    just mean Content redacting off Discovery's bare-bones POI list and
    throwing away Enrichment's work. This still gets the requested
    behaviour that matters in practice: neither crew blocks on being
    *launched*, and the caller doesn't wait for a fully serial
    Discovery->Enrichment->Content chain before Hiker (fully independent)
    even starts.
    """
    city = job.city
    errors: list[str] = []
    hiker_result = {"routes": ""}
    content_result: dict = {}

    def run_hiker() -> None:
        nonlocal hiker_result
        _set_city_status(city, "hiker", "running")
        try:
            hiker_result = HikerCrew(job).kickoff()
            _set_city_status(city, "hiker", "done")
        except Exception as exc:  # noqa: BLE001
            _set_city_status(city, "hiker", "error")
            errors.append(f"hiker: {exc}")
            logger.exception("HikerCrew failed for %s", city)

    hiker_thread = None
    if want_hiker:
        hiker_thread = threading.Thread(target=run_hiker, daemon=True)
        hiker_thread.start()
    else:
        _set_city_status(city, "hiker", "skipped")

    # Option B: poi-discovery (Wikipedia/Google Places, triggered from the
    # app) is the primary content engine. If it already populated this
    # city, running DiscoveryCrew would just re-research what's already
    # there and EnrichmentCrew would re-describe it — burning Anthropic
    # tokens for zero new data. Skip both, go straight to ContentCrew,
    # which narrates/polishes the existing rows instead of discovering
    # from scratch (see _fetch_existing_content_as_discovery_output).
    existing_poi_count = _count_table_rows("points_of_interest", city)

    if existing_poi_count > 0:
        _log(f"[{city}] {existing_poi_count} POIs already exist — skipping Discovery+Enrichment, going straight to Content")
        _set_city_status(city, "discovery", "skipped")
        _set_city_status(city, "enrichment", "skipped")
        _set_city_cache_status(
            city, "content",
            content_at=datetime.now(timezone.utc).isoformat(),
            poi_count=existing_poi_count,
        )
        discovery_output = _fetch_existing_content_as_discovery_output(city)
        enrichment_output: dict = {}
        # Aunque haya lugares, faltan restaurantes: el buscador de negocios
        # trabaja igual (datos reales de OpenStreetMap) y lo que encuentra se
        # guarda directamente. La agenda en vivo la cubre la función
        # live-events (búsqueda web con fecha y fuente); aquí no se inventan
        # eventos con Wikipedia.
        _set_city_status(city, "discovery", "running")
        try:
            fresh = DiscoveryCrew(job).kickoff(only=("businesses",))
            discovery_output["new_businesses"] = fresh.get("businesses", "[]")
            _log(_ingest_direct(job, "business", fresh.get("businesses", "")))
            _set_city_status(city, "discovery", "done")
        except Exception as exc:  # noqa: BLE001
            _set_city_status(city, "discovery", "error")
            errors.append(f"discovery(eventos/negocios): {exc}")
            logger.exception("Slim DiscoveryCrew failed for %s", city)

        def run_content() -> None:
            nonlocal content_result
            _set_city_status(city, "content", "running")
            try:
                content_result = ContentCrew(job).kickoff(discovery_output, enrichment_output)
                _set_city_status(city, "content", "done")
            except Exception as exc:  # noqa: BLE001
                _set_city_status(city, "content", "error")
                errors.append(f"content: {exc}")
                logger.exception("ContentCrew failed for %s", city)

        content_thread = threading.Thread(target=run_content, daemon=True)
        content_thread.start()
        content_thread.join()

    else:
        _set_city_status(city, "discovery", "running")
        _set_city_cache_status(city, "discovery", discovery_at=datetime.now(timezone.utc).isoformat())
        try:
            discovery_output = DiscoveryCrew(job).kickoff()
            # Lugares y negocios reales se guardan ya; el resto del equipo
            # solo mejora descripciones.
            _log(_ingest_direct(job, "poi", discovery_output.get("pois", "")))
            _log(_ingest_direct(job, "business", discovery_output.get("businesses", "")))
            _set_city_status(city, "discovery", "done")
            _set_city_cache_status(city, "discovery", poi_count=_count_table_rows("points_of_interest", city))
        except Exception as exc:  # noqa: BLE001
            _set_city_status(city, "discovery", "error")
            logger.exception("DiscoveryCrew failed for %s", city)
            if hiker_thread:
                hiker_thread.join()
            return {"city": city, "status": "error", "errors": [f"discovery: {exc}"], "director_report": ""}

        enrichment_result: dict = {}

        def run_enrichment_then_content() -> None:
            nonlocal enrichment_result, content_result
            _set_city_status(city, "enrichment", "running")
            _set_city_cache_status(city, "enrichment", enrichment_at=datetime.now(timezone.utc).isoformat())
            try:
                enrichment_result = EnrichmentCrew(job).kickoff(discovery_output)
                _set_city_status(city, "enrichment", "done")
            except Exception as exc:  # noqa: BLE001
                _set_city_status(city, "enrichment", "error")
                errors.append(f"enrichment: {exc}")
                logger.exception("EnrichmentCrew failed for %s", city)

            _set_city_status(city, "content", "running")
            _set_city_cache_status(city, "content", content_at=datetime.now(timezone.utc).isoformat())
            try:
                content_result = ContentCrew(job).kickoff(discovery_output, enrichment_result)
                _set_city_status(city, "content", "done")
            except Exception as exc:  # noqa: BLE001
                _set_city_status(city, "content", "error")
                errors.append(f"content: {exc}")
                logger.exception("ContentCrew failed for %s", city)

        ec_thread = threading.Thread(target=run_enrichment_then_content, daemon=True)
        ec_thread.start()
        ec_thread.join()

    if hiker_thread:
        hiker_thread.join()

    _set_city_status(city, "director", "running")
    director_report = ""
    try:
        director_report = DirectorCrew(job).kickoff(content_result, hiker_result.get("routes", ""))
        _set_city_status(city, "director", "done")
    except Exception as exc:  # noqa: BLE001
        _set_city_status(city, "director", "error")
        errors.append(f"director: {exc}")
        logger.exception("DirectorCrew failed for %s", city)

    return {
        "city": city,
        "status": "error" if errors else "done",
        "errors": errors,
        "director_report": director_report,
    }


def _run_multi_city_in_background(cities: list[CityJob], trigger: str) -> None:
    with run_state_lock:
        run_state["status"] = "running"
        run_state["last_kickoff_at"] = datetime.now(timezone.utc).isoformat()
        run_state["last_trigger"] = trigger
        run_state["cities_last_run"] = [c.city for c in cities]
    _log(f"Kickoff started ({trigger}) — {len(cities)} cities: {', '.join(c.city for c in cities)}")

    failed = []
    try:
        for job in cities:
            try:
                result = _run_pipeline_for_city(job, want_hiker=False)
                _finalize_city_cache(result)
                if result["status"] == "error":
                    failed.append(result)
            finally:
                # Same cumulative thread-leak concern as _run_ingest_job —
                # /kickoff runs every city sequentially in this one loop,
                # so without this the leak has an even tighter, unbroken
                # window to accumulate in than /ingest's pool workers do.
                _reap_leaked_threads(job.city)
                time.sleep(POST_CITY_COOLDOWN_SECONDS)
        with run_state_lock:
            run_state["status"] = "error" if failed else "done"
            run_state["last_finished_at"] = datetime.now(timezone.utc).isoformat()
        _log(f"Kickoff finished — {len(cities) - len(failed)} ok, {len(failed)} failed")
    except Exception as exc:  # noqa: BLE001 — must never crash the background thread silently
        with run_state_lock:
            run_state["status"] = "error"
            run_state["last_finished_at"] = datetime.now(timezone.utc).isoformat()
        _log(f"Kickoff crashed: {exc}")
        logger.exception("_run_multi_city_in_background crashed")


def _check_auth(authorization: str) -> None:
    provided = authorization.removeprefix("Bearer ").strip()
    if not CREWAI_KICKOFF_TOKEN or provided != CREWAI_KICKOFF_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")


async def _read_json_body(request: Request) -> dict:
    """request.json() raises a raw UnicodeDecodeError/JSONDecodeError on a
    malformed body, which FastAPI turns into an unstyled 500 with a full
    traceback leaked to the caller — found while testing the idempotency
    gate above (a non-UTF-8 body byte from a shell encoding quirk, not
    anything the real app client sends, but the endpoint should still
    respond with a normal 400 instead of crashing-looking output)."""
    try:
        return await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid JSON body: {exc}") from exc


@app.post("/kickoff")
async def kickoff(request: Request, authorization: str = Header(default="")):
    _check_auth(authorization)

    body = await _read_json_body(request)
    trigger = body.get("trigger", "manual")
    raw_cities = body.get("cities", [])
    if not isinstance(raw_cities, list) or not raw_cities:
        raise HTTPException(status_code=400, detail="cities must be a non-empty array")

    candidate_cities = [CityJob(**c) for c in raw_cities]

    with run_state_lock:
        already_running = run_state["status"] == "running"
    if already_running:
        return JSONResponse(status_code=409, content={"error": "a kickoff is already running"})

    # Same idempotency gate as /ingest, applied per-city — a daily cron run
    # shouldn't re-process a city that's already complete or mid-flight
    # from some other trigger just because it's in this batch.
    cities: list[CityJob] = []
    skipped: list[dict] = []
    for candidate in candidate_cities:
        allowed, blocking_status = _check_city_cache_gate(candidate.city, candidate.country)
        if allowed:
            cities.append(candidate)
            threading.Thread(
                target=_fetch_wikipedia_summary_and_cache, args=(candidate.city,), daemon=True,
            ).start()
        else:
            skipped.append({"city": candidate.city, "status": blocking_status})

    if not cities:
        return JSONResponse(status_code=202, content={"accepted": True, "city_count": 0, "skipped": skipped})

    thread = threading.Thread(target=_run_multi_city_in_background, args=(cities, trigger), daemon=True)
    thread.start()

    return JSONResponse(status_code=202, content={"accepted": True, "city_count": len(cities), "skipped": skipped})


def _run_ingest_job(job: CityJob, want_hiker: bool) -> None:
    """Executed on the bounded _ingest_executor pool — never a raw
    threading.Thread() (that's what caused RuntimeError: can't start new
    thread under load). Always finalizes city_cache, even on an exception
    this function itself didn't anticipate, so a city never gets stuck
    claimed forever.

    The finally block also reaps whatever leaked CrewAI/litellm threads it
    can and pauses before returning — see _reap_leaked_threads and
    MAX_CONCURRENT_INGESTS's docstring above. This runs on a long-lived
    pool worker thread that gets reused for the *next* submitted city, so
    doing this here, before returning, is what actually happens "before
    starting the next city" for that worker.
    """
    global _ingest_in_flight
    try:
        result = _run_pipeline_for_city(job, want_hiker)
        _finalize_city_cache(result)
    except Exception:  # noqa: BLE001 — pool worker must never die silently
        logger.exception("Unhandled error running pipeline for %s", job.city)
        _set_city_cache_status(job.city, "error", error_message="unhandled worker exception")
    finally:
        try:
            _reap_leaked_threads(job.city)
            time.sleep(POST_CITY_COOLDOWN_SECONDS)
        finally:
            with _ingest_lock:
                _ingest_in_flight = max(0, _ingest_in_flight - 1)


@app.post("/ingest")
async def ingest(request: Request, authorization: str = Header(default="")):
    """Single-city, real-time trigger — e.g. the app calling this the
    moment a user opens a city with no content yet. Responds 202
    immediately; poll GET /status/{city} to see progress and what's
    already available to show (Discovery's POIs land first, usually
    within under a minute).

    Idempotency: rejects with 409 if city_cache already shows this city as
    in-flight or complete (see _check_city_cache_gate). Concurrency: runs
    on a bounded pool (MAX_CONCURRENT_INGESTS) instead of an unbounded raw
    thread per request — extra requests queue inside the pool rather than
    spawning anything or failing.
    """
    _check_auth(authorization)

    body = await _read_json_body(request)
    if "city" not in body:
        raise HTTPException(status_code=400, detail="city is required")

    job = CityJob(**{k: v for k, v in body.items() if k != "mode"})
    want_hiker = body.get("mode") == "hiker"

    allowed, blocking_status = _check_city_cache_gate(job.city, job.country)
    if not allowed:
        return JSONResponse(
            status_code=409,
            content={"error": "already processing or complete", "city": job.city, "status": blocking_status},
        )

    # Fire-and-forget — gives the app's loading screen real content within
    # a second or two, independent of (and much faster than) the pipeline
    # itself. A plain daemon thread is fine here: unlike the old per-request
    # pipeline thread, this one call finishes in a few seconds at most, so
    # it can't accumulate into the same thread-exhaustion problem.
    threading.Thread(target=_fetch_wikipedia_summary_and_cache, args=(job.city,), daemon=True).start()

    global _ingest_in_flight
    with _ingest_lock:
        queued = _ingest_in_flight >= MAX_CONCURRENT_INGESTS
        _ingest_in_flight += 1
    _ingest_executor.submit(_run_ingest_job, job, want_hiker)

    return JSONResponse(
        status_code=202,
        content={"accepted": True, "city": job.city, "hiker": want_hiker, "queued": queued},
    )


@app.get("/status/{city_id}")
async def get_status(city_id: str):
    """Which crews have finished for this city, plus what's actually
    already in Supabase for it right now (the live counts are the source
    of truth and survive a restart; the in-memory crew-by-crew status
    doesn't — if this process restarts mid-run, the crew status resets to
    "pending" even though the data already written stays. That's an
    acceptable tradeoff for a single-instance service: the important
    question — "is there anything to show yet" — is always answered
    correctly from the live counts either way).
    """
    with city_status_lock:
        crews = dict(city_status.get(city_id, {c: "pending" for c in CREWS}))
    crews.pop("updated_at", None)

    data_available = {"pois": 0, "events": 0, "businesses": 0}
    for table, key in (("points_of_interest", "pois"), ("events", "events"), ("businesses", "businesses")):
        try:
            res = supabase.table(table).select("id", count="exact").eq("city", city_id).execute()
            data_available[key] = res.count or 0
        except Exception:  # noqa: BLE001
            pass

    return {"city": city_id, "crews": crews, "data_available": data_available}


def _content_counts() -> list[dict]:
    """Per-city COUNT(*) across the three tables agents write to, same shape
    as the audit queries used in the Supabase pipeline review."""
    counts: dict[str, dict] = {}
    for table, key in (("points_of_interest", "pois"), ("events", "events"), ("businesses", "businesses")):
        try:
            res = supabase.table(table).select("city").execute()
        except Exception:
            continue
        for row in res.data or []:
            city = row["city"]
            counts.setdefault(city, {"city": city, "pois": 0, "events": 0, "businesses": 0})
            counts[city][key] += 1
    return sorted(counts.values(), key=lambda c: c["pois"] + c["events"] + c["businesses"], reverse=True)[:20]


@app.get("/", response_class=HTMLResponse)
async def admin_page():
    with run_state_lock:
        s = dict(run_state)
    with city_status_lock:
        cities_snapshot = {city: dict(v) for city, v in city_status.items()}

    try:
        counts = _content_counts()
    except Exception as exc:  # noqa: BLE001 — admin page must render even if Supabase is unreachable
        counts = []
        logger.warning("Could not load content counts: %s", exc)

    rows_html = "".join(
        f"<tr><td>{escape(c['city'])}</td><td>{c['pois']}</td><td>{c['events']}</td><td>{c['businesses']}</td></tr>"
        for c in counts
    ) or "<tr><td colspan='4'>Sin datos todavía</td></tr>"

    crew_rows_html = "".join(
        f"<tr><td>{escape(city)}</td>" + "".join(f"<td>{escape(v.get(c, '—'))}</td>" for c in CREWS) + "</tr>"
        for city, v in cities_snapshot.items()
    ) or f"<tr><td colspan='{1 + len(CREWS)}'>Sin corridas todavía en este proceso</td></tr>"

    log_html = "".join(
        f"<li><code>{escape(e['timestamp'])}</code> — {escape(e['message'])}</li>" for e in s["log"]
    ) or "<li>Sin ejecuciones registradas todavía</li>"

    crew_header_html = "".join(f"<th>{c}</th>" for c in CREWS)

    status_color = {"idle": "#888", "running": "#e0a800", "done": "#28a745", "error": "#dc3545"}.get(s["status"], "#888")

    return f"""
    <html>
    <head>
      <title>Urban Explorer AI — CrewAI</title>
      <meta charset="utf-8" />
      <style>
        body {{ font-family: -apple-system, sans-serif; max-width: 960px; margin: 40px auto; padding: 0 16px; background: #12151a; color: #e8e8e8; }}
        h1 {{ font-size: 1.4rem; }}
        .status {{ display: inline-block; padding: 4px 12px; border-radius: 12px; background: {status_color}; color: #111; font-weight: 600; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 0.85rem; }}
        th, td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid #333; }}
        button {{ background: #79C7B4; border: none; padding: 10px 18px; border-radius: 8px; font-weight: 600; cursor: pointer; }}
        ul {{ font-size: 0.85rem; max-height: 300px; overflow-y: auto; padding-left: 18px; }}
        section {{ margin-top: 28px; }}
      </style>
    </head>
    <body>
      <h1>Urban Explorer AI — Servicio CrewAI (5 crews: Discovery, Enrichment, Content, Hiker, Director)</h1>
      <p>Estado del último /kickoff: <span class="status">{escape(s['status'])}</span></p>
      <p>Último kickoff: {escape(s['last_kickoff_at'] or '—')}</p>
      <p>Última finalización: {escape(s['last_finished_at'] or '—')}</p>
      <p>Ciudades de la última corrida: {escape(', '.join(s['cities_last_run']) or '—')}</p>

      <section>
        <button onclick="runNow()">Ejecutar /ingest ahora</button>
        <p id="run-result"></p>
      </section>

      <section>
        <h2>Estado de pipeline por ciudad (este proceso)</h2>
        <table>
          <tr><th>Ciudad</th>{crew_header_html}</tr>
          {crew_rows_html}
        </table>
      </section>

      <section>
        <h2>Contenido por ciudad en Supabase (top 20)</h2>
        <table>
          <tr><th>Ciudad</th><th>POIs</th><th>Eventos</th><th>Negocios</th></tr>
          {rows_html}
        </table>
      </section>

      <section>
        <h2>Log de ejecuciones recientes</h2>
        <ul>{log_html}</ul>
      </section>

      <script>
        async function runNow() {{
          const token = prompt("CREWAI_KICKOFF_TOKEN:");
          if (!token) return;
          const city = prompt("Ciudad a procesar (ej: Granada):", "Granada");
          if (!city) return;
          const res = await fetch("/ingest", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json", "Authorization": "Bearer " + token }},
            body: JSON.stringify({{ city }}),
          }});
          const data = await res.json();
          document.getElementById("run-result").innerText = res.status + ": " + JSON.stringify(data);
          if (res.ok) setTimeout(() => location.reload(), 2000);
        }}
      </script>
    </body>
    </html>
    """


@app.get("/health")
async def health():
    return {"ok": True}
