"""Builds and runs the 22-agent crew for one city at a time.

Pipeline per city (crewai.Process.sequential):
  1. 16 research agents run independently (each has its own tools + task,
     no dependency on each other) — monuments, museums, churches, nature,
     hidden gems, hiking POIs, gastronomy, nightlife, hotels, shops,
     experiences, events/festivals, scenic culture, sport, family.
  2. Redactor turns the raw findings into narrative descriptions.
  3. Personalizador enriches with fun_fact/historical_period/accessibility_info.
  4. Agente de Idioma enforces target_language consistency.
  5. Agente de Verificación de Datos rejects anything with bad coordinates,
     an invalid category, or missing required fields.
  6. Agente de Calidad y Ranking assigns the 1-5 rating.
  7. Director de Contenido batches everything by type and is the only agent
     that actually calls send_to_content_ingest.

CrewAI executes tasks in list order for Process.sequential, and each task's
`context` tells it which prior tasks' outputs to read — task 17 onward
therefore always run after all 16 research tasks, in the single chain
described above.
"""
import logging

from crewai import Crew, Process

from agents import AGENT_MODULES
from config import language_for_country
from schemas import CityJob
from tasks import PIPELINE_TASK_MODULES, RESEARCH_TASK_MODULES

logger = logging.getLogger("crewai-urban-explorer")


def build_crew_for_city(job: CityJob) -> Crew:
    language = language_for_country(job.country)
    agent_by_key = {key: module.create_agent() for key, module in AGENT_MODULES}

    tasks = []
    research_tasks = []
    for key, module in RESEARCH_TASK_MODULES:
        task = module.create_task(agent_by_key[key], job.city, job.country or "", job.lat, job.lng, language)
        tasks.append(task)
        research_tasks.append(task)

    context = research_tasks
    for key, module in PIPELINE_TASK_MODULES:
        task = module.create_task(
            agent_by_key[key], job.city, job.country or "", job.lat, job.lng, language, context=context,
        )
        tasks.append(task)
        context = [task]  # each pipeline stage only needs the immediately previous one

    return Crew(
        agents=list(agent_by_key.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )


def run_daily_refresh(cities: list[CityJob], on_city_done=None) -> list[dict]:
    """Runs one crew per city, sequentially (Overpass/Wikipedia are free,
    unauthenticated public APIs shared across the whole run — sequential
    keeps this crew from hammering them with 22-agents-times-N-cities of
    concurrent requests). Returns a per-city result summary for the admin
    UI / run log; never raises — a single city's failure doesn't abort the
    rest of the batch.
    """
    results = []
    for job in cities:
        logger.info("Starting crew for city=%s country=%s", job.city, job.country)
        try:
            crew = build_crew_for_city(job)
            output = crew.kickoff()
            results.append({"city": job.city, "status": "done", "output": str(output)})
        except Exception as exc:  # noqa: BLE001 — one bad city must not kill the batch
            logger.exception("Crew failed for city=%s", job.city)
            results.append({"city": job.city, "status": "error", "error": str(exc)})
        if on_city_done:
            on_city_done(results[-1])
    return results
