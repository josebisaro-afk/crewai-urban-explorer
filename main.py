"""FastAPI service for the Urban Explorer AI content crew.

POST /kickoff  — called daily by supabase/functions/crewai-trigger-refresh
                 (via pg_cron), or manually from the admin UI below.
GET  /         — simple admin/status page: last run, per-city content counts
                 in Supabase, a "Run now" button, and a log of recent runs.
"""
import logging
import threading
from datetime import datetime, timezone
from html import escape

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from config import CREWAI_KICKOFF_TOKEN, supabase
from crew import run_daily_refresh
from schemas import CityJob

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crewai-urban-explorer")

app = FastAPI(title="Urban Explorer AI — CrewAI content service")

MAX_LOG_ENTRIES = 30

# Single-process in-memory state — fine for one Railway instance; if this
# ever scales to multiple instances, move this to a Supabase table instead.
state = {
    "status": "idle",  # idle | running | done | error
    "last_kickoff_at": None,
    "last_finished_at": None,
    "last_trigger": None,
    "cities_last_run": [],
    "log": [],  # list of {timestamp, message}
}
state_lock = threading.Lock()


def _log(message: str) -> None:
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "message": message}
    logger.info(message)
    with state_lock:
        state["log"].insert(0, entry)
        state["log"] = state["log"][:MAX_LOG_ENTRIES]


def _run_crew_in_background(cities: list[CityJob], trigger: str) -> None:
    with state_lock:
        state["status"] = "running"
        state["last_kickoff_at"] = datetime.now(timezone.utc).isoformat()
        state["last_trigger"] = trigger
        state["cities_last_run"] = [c.city for c in cities]
    _log(f"Kickoff started ({trigger}) — {len(cities)} cities: {', '.join(c.city for c in cities)}")

    try:
        results = run_daily_refresh(cities, on_city_done=lambda r: _log(
            f"City '{r['city']}': {r['status']}" + (f" — {r.get('error')}" if r.get("error") else "")
        ))
        failed = [r for r in results if r["status"] == "error"]
        with state_lock:
            state["status"] = "error" if failed else "done"
            state["last_finished_at"] = datetime.now(timezone.utc).isoformat()
        _log(f"Kickoff finished — {len(results) - len(failed)} ok, {len(failed)} failed")
    except Exception as exc:  # noqa: BLE001 — must never crash the background thread silently
        with state_lock:
            state["status"] = "error"
            state["last_finished_at"] = datetime.now(timezone.utc).isoformat()
        _log(f"Kickoff crashed: {exc}")
        logger.exception("run_daily_refresh crashed")


@app.post("/kickoff")
async def kickoff(request: Request, authorization: str = Header(default="")):
    provided = authorization.removeprefix("Bearer ").strip()
    if not CREWAI_KICKOFF_TOKEN or provided != CREWAI_KICKOFF_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")

    body = await request.json()
    trigger = body.get("trigger", "manual")
    raw_cities = body.get("cities", [])
    if not isinstance(raw_cities, list) or not raw_cities:
        raise HTTPException(status_code=400, detail="cities must be a non-empty array")

    cities = [CityJob(**c) for c in raw_cities]

    with state_lock:
        already_running = state["status"] == "running"
    if already_running:
        return JSONResponse(status_code=409, content={"error": "a kickoff is already running"})

    thread = threading.Thread(target=_run_crew_in_background, args=(cities, trigger), daemon=True)
    thread.start()

    return JSONResponse(status_code=202, content={"accepted": True, "city_count": len(cities)})


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
    with state_lock:
        s = dict(state)

    try:
        counts = _content_counts()
    except Exception as exc:  # noqa: BLE001 — admin page must render even if Supabase is unreachable
        counts = []
        logger.warning("Could not load content counts: %s", exc)

    rows_html = "".join(
        f"<tr><td>{escape(c['city'])}</td><td>{c['pois']}</td><td>{c['events']}</td><td>{c['businesses']}</td></tr>"
        for c in counts
    ) or "<tr><td colspan='4'>Sin datos todavía</td></tr>"

    log_html = "".join(
        f"<li><code>{escape(e['timestamp'])}</code> — {escape(e['message'])}</li>" for e in s["log"]
    ) or "<li>Sin ejecuciones registradas todavía</li>"

    status_color = {"idle": "#888", "running": "#e0a800", "done": "#28a745", "error": "#dc3545"}.get(s["status"], "#888")

    return f"""
    <html>
    <head>
      <title>Urban Explorer AI — CrewAI</title>
      <meta charset="utf-8" />
      <style>
        body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 16px; background: #12151a; color: #e8e8e8; }}
        h1 {{ font-size: 1.4rem; }}
        .status {{ display: inline-block; padding: 4px 12px; border-radius: 12px; background: {status_color}; color: #111; font-weight: 600; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        th, td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid #333; }}
        button {{ background: #79C7B4; border: none; padding: 10px 18px; border-radius: 8px; font-weight: 600; cursor: pointer; }}
        ul {{ font-size: 0.85rem; max-height: 300px; overflow-y: auto; padding-left: 18px; }}
        section {{ margin-top: 28px; }}
      </style>
    </head>
    <body>
      <h1>Urban Explorer AI — Servicio CrewAI (22 agentes)</h1>
      <p>Estado: <span class="status">{escape(s['status'])}</span></p>
      <p>Último kickoff: {escape(s['last_kickoff_at'] or '—')}</p>
      <p>Última finalización: {escape(s['last_finished_at'] or '—')}</p>
      <p>Ciudades de la última corrida: {escape(', '.join(s['cities_last_run']) or '—')}</p>

      <section>
        <button onclick="runNow()">Ejecutar ahora</button>
        <p id="run-result"></p>
      </section>

      <section>
        <h2>Contenido por ciudad (top 20)</h2>
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
          const res = await fetch("/kickoff", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json", "Authorization": "Bearer " + token }},
            body: JSON.stringify({{
              trigger: "manual_admin_ui",
              triggered_at: new Date().toISOString(),
              cities: [{{ city }}],
            }}),
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
