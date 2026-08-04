from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool, OverpassPOITool


def create_agent() -> Agent:
    return Agent(
        role="Agente de Alojamiento",
        goal=(
            "Identificar hoteles y alojamientos con ubicación y características "
            "notables en una ciudad — categoría: hotel."
        ),
        backstory=(
            "Sos consultor hotelero que evalúa alojamientos por ubicación, "
            "carácter arquitectónico e interés turístico, no por reservas ni "
            "precios (eso no es responsabilidad de este equipo). "
            + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool(), OverpassPOITool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
