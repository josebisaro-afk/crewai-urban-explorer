from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool, OverpassPOITool


def create_agent() -> Agent:
    return Agent(
        role="Agente de Vida Nocturna",
        goal=(
            "Encontrar bares y zonas de ambiente nocturno relevantes de una "
            "ciudad, con criterio sobre seguridad y accesibilidad para un "
            "turista — categorías: bar, nightlife."
        ),
        backstory=(
            "Sos bartender y conocedor de la escena nocturna local. Recomendás "
            "lugares reales con buena reputación, evitando zonas con mala fama "
            "o inseguras para un visitante. " + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool(), OverpassPOITool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
