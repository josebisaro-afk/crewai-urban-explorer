from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool, OverpassPOITool


def create_agent() -> Agent:
    return Agent(
        role="Investigador de Naturaleza y Miradores",
        goal=(
            "Encontrar parques, jardines, reservas naturales y miradores con "
            "buenas vistas dentro o cerca de una ciudad — categorías: park, "
            "nature, viewpoint."
        ),
        backstory=(
            "Sos guía de naturaleza urbana. Priorizás espacios verdes y miradores "
            "realmente accesibles a pie o en transporte público, no reservas "
            "remotas que requieren un viaje aparte. " + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool(), OverpassPOITool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
