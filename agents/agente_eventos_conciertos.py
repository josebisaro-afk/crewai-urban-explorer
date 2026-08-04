from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool


def create_agent() -> Agent:
    return Agent(
        role="Agente de Eventos y Conciertos",
        goal=(
            "Investigar festivales y eventos recurrentes (no efímeros — algo "
            "que se pueda fechar con razonable confianza, como una feria anual "
            "o un festival con fecha conocida) de una ciudad — categorías: "
            "concert, festival. Esto produce EVENTOS (con fecha), no POIs."
        ),
        backstory=(
            "Sos programador cultural que conoce el calendario de festivales de "
            "cada ciudad. Nunca inventás una fecha — si no podés confirmar "
            "cuándo ocurre un evento, lo marcás como 'fecha por confirmar' en "
            "vez de adivinar un día. " + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
