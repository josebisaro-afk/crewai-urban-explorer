from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool, OverpassPOITool


def create_agent() -> Agent:
    return Agent(
        role="Agente de Compras",
        goal=(
            "Encontrar tiendas, mercados y zonas comerciales con identidad local "
            "(artesanía, productos típicos) en una ciudad — categoría: shop."
        ),
        backstory=(
            "Sos comprador personal especializado en artesanía y productos "
            "locales auténticos. Evitás recomendar cadenas genéricas que un "
            "turista podría encontrar en cualquier ciudad. " + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool(), OverpassPOITool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
