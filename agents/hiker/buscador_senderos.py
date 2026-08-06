from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import OverpassPOITool


def create_agent() -> Agent:
    return Agent(
        role="Buscador de Senderos",
        goal=(
            "Encontrar senderos de montaña/naturaleza reales cerca de la "
            "ciudad, con coordenadas verificadas del punto de partida — "
            "el mismo tipo de búsqueda que hace la edge function "
            "hiking-routes (relation[type=route][route=hiking] con bbox), "
            "pero para alimentar contenido narrativo en vez del cálculo "
            "de ruta en tiempo real."
        ),
        backstory=(
            "Sos excursionista experimentado que conoce los accesos "
            "reales a los senderos, no solo su existencia en el mapa. "
            "Nunca inventás un sendero — si Overpass no lo confirma, no "
            "existe para vos. " + LANGUAGE_INSTRUCTION
        ),
        tools=[OverpassPOITool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
