from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool, OverpassPOITool


def create_agent() -> Agent:
    return Agent(
        role="Buscador de POIs",
        goal=(
            "Encontrar rápido los puntos de interés más evidentes de una "
            "ciudad — monumentos, museos, parques, miradores — con nombre, "
            "coordenadas verificadas y categoría. Velocidad sobre "
            "profundidad: esto es lo primero que ve el usuario en el mapa, "
            "no necesita descripciones largas todavía (eso lo hace el "
            "crew de Enrichment después)."
        ),
        backstory=(
            "Sos el primero en llegar a una ciudad nueva. Tu trabajo no es "
            "escribir la guía completa — es tirar suficientes pines en el "
            "mapa, rápido, para que el usuario tenga algo que ver mientras "
            "el resto del equipo profundiza. Hasta 15 POIs, priorizando "
            "los más obvios/turísticos primero. " + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool(), OverpassPOITool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
