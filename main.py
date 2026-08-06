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
import logging
import threading
from datetime import datetime, timezone
from html import escape

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

    _set_city_status(city, "discovery", "running")
    try:
        discovery_output = DiscoveryCrew(job).kickoff()
        _set_city_status(city, "discovery", "done")
    except Exception as exc:  # noqa: BLE001
        _set_city_status(city, "discovery", "error")
        logger.exception("DiscoveryCrew failed for %s", city)
        if hiker_thread:
            hiker_thread.join()
        return {"city": city, "status": "error", "errors": [f"discovery: {exc}"], "director_report": ""}

    enrichment_result: dict = {}
    content_result: dict = {}

    def run_enrichment_then_content() -> None:
        nonlocal enrichment_result, content_result
        _set_city_status(city, "enrichment", "running")
        try:
            enrichment_result = EnrichmentCrew(job).kickoff(discovery_output)
            _set_city_status(city, "enrichment", "done")
        except Exception as exc:  # noqa: BLE001
            _set_city_status(city, "enrichment", "error")
            errors.append(f"enrichment: {exc}")
            logger.exception("EnrichmentCrew failed for %s", city)

        _set_city_status(city, "content", "running")
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
            result = _run_pipeline_for_city(job, want_hiker=False)
            if result["status"] == "error":
                failed.append(result)
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


@app.post("/kickoff")
async def kickoff(request: Request, authorization: str = Header(default="")):
    _check_auth(authorization)

    body = await request.json()
    trigger = body.get("trigger", "manual")
    raw_cities = body.get("cities", [])
    if not isinstance(raw_cities, list) or not raw_cities:
        raise HTTPException(status_code=400, detail="cities must be a non-empty array")

    cities = [CityJob(**c) for c in raw_cities]

    with run_state_lock:
        already_running = run_state["status"] == "running"
    if already_running:
        return JSONResponse(status_code=409, content={"error": "a kickoff is already running"})

    thread = threading.Thread(target=_run_multi_city_in_background, args=(cities, trigger), daemon=True)
    thread.start()

    return JSONResponse(status_code=202, content={"accepted": True, "city_count": len(cities)})


@app.post("/ingest")
async def ingest(request: Request, authorization: str = Header(default="")):
    """Single-city, real-time trigger — e.g. the app calling this the
    moment a user opens a city with no content yet. Responds 202
    immediately; poll GET /status/{city} to see progress and what's
    already available to show (Discovery's POIs land first, usually
    within under a minute)."""
    _check_auth(authorization)

    body = await request.json()
    if "city" not in body:
        raise HTTPException(status_code=400, detail="city is required")

    job = CityJob(**{k: v for k, v in body.items() if k != "mode"})
    want_hiker = body.get("mode") == "hiker"

    thread = threading.Thread(target=_run_pipeline_for_city, args=(job, want_hiker), daemon=True)
    thread.start()

    return JSONResponse(status_code=202, content={"accepted": True, "city": job.city, "hiker": want_hiker})


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
