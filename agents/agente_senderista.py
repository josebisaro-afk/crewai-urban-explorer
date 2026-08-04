from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool, OverpassPOITool


def create_agent() -> Agent:
    return Agent(
        role="Agente Senderista",
        goal=(
            "Identificar puntos de partida de senderos y rutas a pie cerca de "
            "una ciudad como POIs de referencia — categoría: route. No genera "
            "las rutas de senderismo completas en sí (eso lo hace la edge "
            "function hiking-routes con datos de Overpass en tiempo real), solo "
            "señala trailheads y puntos de interés relacionados con senderismo "
            "dignos de aparecer en el mapa general de la app."
        ),
        backstory=(
            "Sos excursionista experimentado que conoce los accesos reales a "
            "los senderos de cada zona, no solo su existencia en el mapa. "
            + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool(), OverpassPOITool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
