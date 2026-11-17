"""Trabajo de los agentes para GitHub Actions (sin servidor).

Cada vez que GitHub lo arranca (cada 2 horas, o a mano desde la pestaña
Actions):
  1. Le pregunta a Supabase qué ciudades necesitan agentes
     (RPC agent_next_cities: ciudades nuevas, pendientes, con error hace
     más de 24 h, atascadas más de 3 h, o completas hace más de 30 días).
  2. Corre el mismo pipeline de 5 equipos que usaba el servidor de Railway
     (main._run_pipeline_for_city), una ciudad detrás de otra.
  3. Deja el resultado en city_cache (complete / error) para que la app y
     la próxima corrida lo vean.

Uso:
  python run_job.py                      # la cola, hasta 2 ciudades
  python run_job.py --max 3
  python run_job.py --city "Košice"      # una ciudad concreta (debe estar en city_index)
  python run_job.py --city "Košice" --hiker
"""
import argparse
import logging
import time

import httpx
import sys
from datetime import datetime, timezone

from config import supabase
from schemas import CityJob

# main.py trae el pipeline y los helpers de city_cache. Importarlo crea la
# app FastAPI pero no levanta ningún servidor.
import main  # noqa: E402

logger = logging.getLogger("crewai-urban-explorer")
MAX_CITIES_HARD_LIMIT = 5


def _queue(limit: int) -> list[CityJob]:
    res = supabase.rpc("agent_next_cities", {"p_limit": limit}).execute()
    jobs = []
    for row in res.data or []:
        jobs.append(CityJob(city=row["city"], country=row.get("country"), lat=row.get("lat"), lng=row.get("lng")))
        logger.info("En cola: %s (%s)", row["city"], row.get("reason"))
    return jobs


def _one_city(name: str) -> list[CityJob]:
    res = supabase.table("city_index").select("city,country,center_lat,center_lng").eq("city", name).limit(1).execute()
    rows = res.data or []
    if not rows:
        logger.error("La ciudad %s no está en city_index: ábrela primero en la app.", name)
        return []
    r = rows[0]
    return [CityJob(city=r["city"], country=r.get("country") or None, lat=r.get("center_lat"), lng=r.get("center_lng"))]


def _country_for(job: CityJob) -> str | None:
    """Si city_index no trae país, lo pregunta a OpenStreetMap (GitHub sí
    puede usar Nominatim; Supabase no). Así los datos no salen como 'Spain'."""
    if job.country or job.lat is None or job.lng is None:
        return job.country
    try:
        time.sleep(1.1)  # Nominatim: máximo 1 petición por segundo
        r = httpx.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": job.lat, "lon": job.lng, "format": "json", "zoom": 3, "accept-language": "es"},
            headers={"User-Agent": "UrbanExplorerAI-Agentes/1.0 (contact@urbanexplorer.app)"},
            timeout=10,
        )
        country = (r.json().get("address") or {}).get("country")
        if country:
            supabase.table("city_index").update({"country": country}).eq("city", job.city).execute()
        return country or None
    except Exception:  # noqa: BLE001
        logger.warning("No pude averiguar el país de %s", job.city)
        return None


def _claim(city: str, country: str | None) -> None:
    """Marca la ciudad como 'pending' aunque estuviera completa o atascada:
    la cola ya decidió que le toca."""
    main._set_city_cache_status(
        city, "pending",
        country=country,
        triggered_at=datetime.now(timezone.utc).isoformat(),
        error_message=None,
    )


def run(jobs: list[CityJob], want_hiker: bool) -> int:
    failed = 0
    for job in jobs:
        job.country = _country_for(job)
        logger.info("=== Agentes trabajando en %s (%s) ===", job.city, job.country or "país desconocido")
        _claim(job.city, job.country)
        try:
            result = main._run_pipeline_for_city(job, want_hiker)
            main._finalize_city_cache(result)
            logger.info("Resultado %s: %s %s", job.city, result["status"], result.get("errors"))
            logger.info("Informe del Director:\n%s", result.get("director_report", "")[:4000])
            if result["status"] == "error":
                failed += 1
        except Exception:  # noqa: BLE001
            logger.exception("Fallo inesperado en %s", job.city)
            main._set_city_cache_status(job.city, "error", error_message="fallo inesperado en run_job")
            failed += 1
        finally:
            main._reap_leaked_threads(job.city)
    return failed


def cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", default="")
    parser.add_argument("--max", type=int, default=2)
    parser.add_argument("--hiker", action="store_true")
    args = parser.parse_args()

    limit = max(1, min(args.max, MAX_CITIES_HARD_LIMIT))
    jobs = _one_city(args.city.strip()) if args.city.strip() else _queue(limit)
    if not jobs:
        logger.info("No hay ciudades pendientes. Nada que hacer.")
        return 0
    failed = run(jobs, args.hiker)
    logger.info("Terminado: %d ciudad(es), %d con error.", len(jobs), failed)
    return 1 if failed else 0  # en rojo en GitHub si alguna ciudad falló


if __name__ == "__main__":
    sys.exit(cli())
