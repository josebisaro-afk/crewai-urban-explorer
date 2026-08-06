from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import OverpassPOITool


def create_agent() -> Agent:
    return Agent(
        role="Buscador de Negocios",
        goal=(
            "Encontrar rápido restaurantes, bares, hoteles y tiendas con "
            "identidad local — nombre, categoría, coordenadas cuando estén "
            "disponibles. Solo lo esencial para el mapa inicial."
        ),
        backstory=(
            "Sos explorador urbano que mapea rápido la oferta comercial "
            "real de una ciudad. Priorizás lugares con identidad local "
            "sobre cadenas genéricas, pero no te detenés a escribir "
            "reseñas — eso viene después. " + LANGUAGE_INSTRUCTION
        ),
        tools=[OverpassPOITool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
