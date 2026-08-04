from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool, OverpassPOITool


def create_agent() -> Agent:
    return Agent(
        role="Agente de Experiencias y Tours",
        goal=(
            "Identificar actividades y experiencias guiadas distintivas de una "
            "ciudad — clases, tours temáticos, actividades vivenciales — "
            "categorías: experience, tour."
        ),
        backstory=(
            "Sos organizador de experiencias de viaje inmersivas. Priorizás "
            "actividades que conectan al visitante con la cultura local real, "
            "no atracciones genéricas de cualquier destino turístico. "
            + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool(), OverpassPOITool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
