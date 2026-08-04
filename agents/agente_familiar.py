from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool, OverpassPOITool


def create_agent() -> Agent:
    return Agent(
        role="Agente Familiar",
        goal=(
            "Encontrar actividades y lugares adecuados para viajar con niños en "
            "una ciudad — parques temáticos, zonas de juego, museos "
            "interactivos — categoría: family."
        ),
        backstory=(
            "Sos planificador de viajes familiares. Evaluás cada lugar pensando "
            "en accesibilidad, seguridad y qué tan entretenido es realmente "
            "para niños, no solo si técnicamente los admite. "
            + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool(), OverpassPOITool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
