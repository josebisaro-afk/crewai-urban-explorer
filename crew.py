"""Five separate crews, each its own crewai.Crew — replaces the old single
22-agent crew. Splitting them lets Discovery return fast (~30s) so the app
can show map pins immediately, while Enrichment and Content keep working
in the background, and Hiker only spins up when actually needed.

Because each crew is its own crewai.Crew instance, crewai's native
Task(context=[...]) linking (which only pulls .output from *sibling* tasks
inside the same Crew's task list) can't carry data between crews. Within
one crew that native linking is used as normal (see ContentCrew's and
HikerCrew's internal task chains). Between crews, the previous crew's
task outputs are read back as plain strings (task.output.raw) and
injected directly into the next crew's task descriptions instead — see
_task_outputs() below.

Known gap, by design: HikerCrew's output (trailhead name + narration) is
reported by DirectorCrew but never written to the `hiking_routes` Supabase
table. That table's rows need real trail geometry (path, distance_km,
elevation_gain_m) computed from actual Overpass polylines — which is what
supabase/functions/hiking-routes (in the urban-explorer-ai repo) already
does in real time when a user opens Hiker Mode. This crew's agents never
see that geometry (buscador_senderos only gets a name + start point from
Overpass), so writing its output into that table would silently degrade
rows the app's UI depends on (distance/elevation/duration cards). Wiring
Hiker crew's narrative output into that table for real would mean either
enriching the edge function's output with this content, or teaching
buscador_senderos to fetch and carry full trail geometry — neither
attempted here.
"""
import logging

from crewai import Crew, Process, Task

from config import language_for_country
from schemas import CityJob

from agents.discovery import buscador_pois as d_pois_agent
from agents.discovery import buscador_eventos as d_events_agent
from agents.discovery import buscador_negocios as d_biz_agent
from agents.discovery import clima_contexto as d_weather_agent
from tasks.discovery import buscador_pois as d_pois_task
from tasks.discovery import buscador_eventos as d_events_task
from tasks.discovery import buscador_negocios as d_biz_task
from tasks.discovery import clima_contexto as d_weather_task

from agents.enrichment import enriquecedor_pois as e_pois_agent
from agents.enrichment import investigador_historia as e_historia_agent
from agents.enrichment import investigador_cultura as e_cultura_agent
from agents.enrichment import extractor_horarios as e_horarios_agent
from agents.enrichment import extractor_precios as e_precios_agent
from tasks.enrichment import enriquecedor_pois as e_pois_task
from tasks.enrichment import investigador_historia as e_historia_task
from tasks.enrichment import investigador_cultura as e_cultura_task
from tasks.enrichment import extractor_horarios as e_horarios_task
from tasks.enrichment import extractor_precios as e_precios_task

from agents.content import redactor_contenido as c_redactor_agent
from agents.content import personalizador_contenido as c_personalizador_agent
from agents.content import verificador_calidad as c_verificador_agent
from agents.content import traductor_idiomas as c_traductor_agent
from agents.content import generador_rutas_tematicas as c_rutas_agent
from tasks.content import redactor_contenido as c_redactor_task
from tasks.content import personalizador_contenido as c_personalizador_task
from tasks.content import verificador_calidad as c_verificador_task
from tasks.content import traductor_idiomas as c_traductor_task
from tasks.content import generador_rutas_tematicas as c_rutas_task

from agents.hiker import buscador_senderos as h_senderos_agent
from agents.hiker import verificador_rutas as h_verificador_agent
from agents.hiker import clima_montana as h_clima_agent
from agents.hiker import identificador_plantas as h_plantas_agent
from agents.hiker import guia_senderismo as h_guia_agent
from tasks.hiker import buscador_senderos as h_senderos_task
from tasks.hiker import verificador_rutas as h_verificador_task
from tasks.hiker import clima_montana as h_clima_task
from tasks.hiker import identificador_plantas as h_plantas_task
from tasks.hiker import guia_senderismo as h_guia_task

from agents.director import director_contenido as dir_agent
from tasks.director import director_contenido as dir_task

logger = logging.getLogger("crewai-urban-explorer")


def _task_outputs(tasks: dict) -> dict:
    """Reads each task's raw text output after crew.kickoff() has run."""
    return {key: (str(task.output.raw) if task.output else "") for key, task in tasks.items()}


class DiscoveryCrew:
    """4 agents, independent of each other — fast first pass so the app can
    show map pins almost immediately."""

    def __init__(self, job: CityJob):
        self.job = job
        self.language = language_for_country(job.country)

    def kickoff(self) -> dict:
        j = self.job
        agents = {
            "pois": d_pois_agent.create_agent(),
            "events": d_events_agent.create_agent(),
            "businesses": d_biz_agent.create_agent(),
            "weather": d_weather_agent.create_agent(),
        }
        tasks: dict[str, Task] = {
            "pois": d_pois_task.create_task(agents["pois"], j.city, j.country or "", j.lat, j.lng, self.language),
            "events": d_events_task.create_task(agents["events"], j.city, j.country or "", j.lat, j.lng, self.language),
            "businesses": d_biz_task.create_task(agents["businesses"], j.city, j.country or "", j.lat, j.lng, self.language),
            "weather": d_weather_task.create_task(agents["weather"], j.city, j.country or "", j.lat, j.lng, self.language),
        }
        crew = Crew(agents=list(agents.values()), tasks=list(tasks.values()), process=Process.sequential, verbose=True)
        crew.kickoff()
        return _task_outputs(tasks)


class EnrichmentCrew:
    """5 agents, all independently deepening Discovery's output — none
    depend on each other, only on what Discovery already found."""

    def __init__(self, job: CityJob):
        self.job = job
        self.language = language_for_country(job.country)

    def kickoff(self, discovery_output: dict) -> dict:
        j = self.job
        pois_json = discovery_output.get("pois", "[]")
        biz_json = discovery_output.get("businesses", "[]")

        agents = {
            "pois": e_pois_agent.create_agent(),
            "historia": e_historia_agent.create_agent(),
            "cultura": e_cultura_agent.create_agent(),
            "horarios": e_horarios_agent.create_agent(),
            "precios": e_precios_agent.create_agent(),
        }
        tasks: dict[str, Task] = {
            "pois": e_pois_task.create_task(agents["pois"], j.city, j.country or "", j.lat, j.lng, self.language, pois_json),
            "historia": e_historia_task.create_task(agents["historia"], j.city, j.country or "", j.lat, j.lng, self.language, pois_json),
            "cultura": e_cultura_task.create_task(agents["cultura"], j.city, j.country or "", j.lat, j.lng, self.language, pois_json, biz_json),
            "horarios": e_horarios_task.create_task(agents["horarios"], j.city, j.country or "", j.lat, j.lng, self.language, pois_json, biz_json),
            "precios": e_precios_task.create_task(agents["precios"], j.city, j.country or "", j.lat, j.lng, self.language, biz_json),
        }
        crew = Crew(agents=list(agents.values()), tasks=list(tasks.values()), process=Process.sequential, verbose=True)
        crew.kickoff()
        return _task_outputs(tasks)


class ContentCrew:
    """5 agents chained sequentially within this one crew: Redactor ->
    Personalizador -> Verificador de Calidad -> Traductor -> Generador de
    Rutas Temáticas. Starts from Discovery+Enrichment's combined output."""

    def __init__(self, job: CityJob):
        self.job = job
        self.language = language_for_country(job.country)

    def kickoff(self, discovery_output: dict, enrichment_output: dict) -> dict:
        j = self.job
        agents = {
            "redactor": c_redactor_agent.create_agent(),
            "personalizador": c_personalizador_agent.create_agent(),
            "verificador": c_verificador_agent.create_agent(),
            "traductor": c_traductor_agent.create_agent(),
            "rutas": c_rutas_agent.create_agent(),
        }

        redactor_t = c_redactor_task.create_task(
            agents["redactor"], j.city, j.country or "", j.lat, j.lng, self.language,
            discovery_output, enrichment_output,
        )
        personalizador_t = c_personalizador_task.create_task(
            agents["personalizador"], j.city, j.country or "", j.lat, j.lng, self.language, [redactor_t],
        )
        verificador_t = c_verificador_task.create_task(
            agents["verificador"], j.city, j.country or "", j.lat, j.lng, self.language, [personalizador_t],
        )
        traductor_t = c_traductor_task.create_task(
            agents["traductor"], j.city, j.country or "", j.lat, j.lng, self.language, [verificador_t],
        )
        rutas_t = c_rutas_task.create_task(
            agents["rutas"], j.city, j.country or "", j.lat, j.lng, self.language, [traductor_t],
        )

        tasks: dict[str, Task] = {
            "redactor": redactor_t, "personalizador": personalizador_t,
            "verificador": verificador_t, "traductor": traductor_t, "rutas": rutas_t,
        }
        crew = Crew(agents=list(agents.values()), tasks=list(tasks.values()), process=Process.sequential, verbose=True)
        crew.kickoff()
        outputs = _task_outputs(tasks)
        return {"final_content": outputs["traductor"], "routes": outputs["rutas"]}


class HikerCrew:
    """5 agents chained within this one crew: Buscador de Senderos ->
    Verificador de Rutas -> (Clima de Montaña + Identificador de Plantas,
    both depending only on the verified routes) -> Guía de Senderismo.
    Only run when the request explicitly asks for Hiker Mode content."""

    def __init__(self, job: CityJob):
        self.job = job
        self.language = language_for_country(job.country)

    def kickoff(self) -> dict:
        j = self.job
        agents = {
            "senderos": h_senderos_agent.create_agent(),
            "verificador": h_verificador_agent.create_agent(),
            "clima": h_clima_agent.create_agent(),
            "plantas": h_plantas_agent.create_agent(),
            "guia": h_guia_agent.create_agent(),
        }

        senderos_t = h_senderos_task.create_task(agents["senderos"], j.city, j.country or "", j.lat, j.lng, self.language)
        verificador_t = h_verificador_task.create_task(
            agents["verificador"], j.city, j.country or "", j.lat, j.lng, self.language, [senderos_t],
        )
        clima_t = h_clima_task.create_task(
            agents["clima"], j.city, j.country or "", j.lat, j.lng, self.language, [verificador_t],
        )
        plantas_t = h_plantas_task.create_task(
            agents["plantas"], j.city, j.country or "", j.lat, j.lng, self.language, [verificador_t],
        )
        guia_t = h_guia_task.create_task(
            agents["guia"], j.city, j.country or "", j.lat, j.lng, self.language,
            [verificador_t, clima_t, plantas_t],
        )

        tasks: dict[str, Task] = {
            "senderos": senderos_t, "verificador": verificador_t,
            "clima": clima_t, "plantas": plantas_t, "guia": guia_t,
        }
        crew = Crew(agents=list(agents.values()), tasks=list(tasks.values()), process=Process.sequential, verbose=True)
        crew.kickoff()
        outputs = _task_outputs(tasks)
        return {"routes": outputs["guia"]}


class DirectorCrew:
    """1 agent, always the final step — the only crew (and only agent
    across all 5 crews) that actually writes to Supabase."""

    def __init__(self, job: CityJob):
        self.job = job
        self.language = language_for_country(job.country)

    def kickoff(self, content_output: dict, hiker_output: str = "") -> str:
        j = self.job
        agent = dir_agent.create_agent()
        task = dir_task.create_task(
            agent, j.city, j.country or "", j.lat, j.lng, self.language,
            content_output.get("final_content", "[]"), hiker_output,
        )
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
        result = crew.kickoff()
        return str(result.raw) if result else ""
