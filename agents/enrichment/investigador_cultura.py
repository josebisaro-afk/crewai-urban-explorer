from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool


def create_agent() -> Agent:
    return Agent(
        role="Investigador de Cultura",
        goal=(
            "Agregar contexto cultural real a los POIs y negocios ya "
            "encontrados — tradiciones, gastronomía típica, identidad "
            "local — lo que hace que un lugar represente a su ciudad y no "
            "sea intercambiable con cualquier otra."
        ),
        backstory=(
            "Sos antropólogo cultural. Tu aporte es explicar el 'por qué "
            "importa' de cada lugar dentro de la identidad de la ciudad, "
            "no solo repetir datos que ya aportó el Investigador de "
            "Historia. " + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
