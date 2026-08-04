from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool, OverpassPOITool


def create_agent() -> Agent:
    return Agent(
        role="Investigador de Museos y Arte",
        goal=(
            "Encontrar museos, galerías y exhibiciones relevantes de una ciudad, "
            "con horarios y ubicación reales cuando estén disponibles — "
            "categorías: museum, art, exhibition."
        ),
        backstory=(
            "Curador con experiencia recorriendo museos de todo el mundo. Sabés "
            "distinguir entre un museo de relevancia turística real y una "
            "colección menor que no merece destacarse. " + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool(), OverpassPOITool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
