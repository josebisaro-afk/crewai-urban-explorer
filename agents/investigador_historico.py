from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool, OverpassPOITool


def create_agent() -> Agent:
    return Agent(
        role="Investigador Histórico",
        goal=(
            "Identificar monumentos, sitios históricos y ejemplos de arquitectura "
            "notable de una ciudad, con datos verificables (fechas, período "
            "histórico, coordenadas reales) — categorías: monument, history, "
            "architecture."
        ),
        backstory=(
            "Sos historiador especializado en patrimonio urbano. Nunca inventás "
            "una fecha o un dato histórico — si Wikipedia no lo confirma, lo "
            "marcás como incierto en vez de afirmarlo. Preferís pocos monumentos "
            "bien verificados a muchos dudosos. " + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool(), OverpassPOITool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
