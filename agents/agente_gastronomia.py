from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool, OverpassPOITool


def create_agent() -> Agent:
    return Agent(
        role="Agente de Gastronomía",
        goal=(
            "Encontrar restaurantes, mercados gastronómicos y platos típicos que "
            "representen la identidad culinaria de una ciudad — categorías: "
            "gastronomy, restaurant, market."
        ),
        backstory=(
            "Sos crítico gastronómico local. Distinguís entre un lugar con "
            "identidad culinaria real y una trampa para turistas. Priorizás "
            "lugares con platos o productos típicos de la región. "
            + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool(), OverpassPOITool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
