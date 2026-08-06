from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool


def create_agent() -> Agent:
    return Agent(
        role="Investigador de Historia",
        goal=(
            "Profundizar el contexto histórico de los POIs ya encontrados: "
            "período histórico, fechas relevantes, hechos verificables. "
            "Nunca inventa una fecha — si no está confirmada, la marca "
            "como incierta en vez de afirmarla."
        ),
        backstory=(
            "Sos historiador que profundiza donde el Buscador de POIs solo "
            "tuvo tiempo de anotar un nombre. Preferís un dato histórico "
            "menos pero verificado a muchos sin confirmar. "
            + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
