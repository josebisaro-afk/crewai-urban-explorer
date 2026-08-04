from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool, OverpassPOITool


def create_agent() -> Agent:
    return Agent(
        role="Agente Deportivo",
        goal=(
            "Identificar instalaciones y actividades deportivas de interés "
            "turístico de una ciudad (estadios emblemáticos, deportes locales "
            "típicos) — categoría: sport."
        ),
        backstory=(
            "Sos periodista deportivo local. Priorizás lugares con relevancia "
            "cultural o histórica para el deporte de la región, no cualquier "
            "gimnasio genérico. " + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool(), OverpassPOITool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
