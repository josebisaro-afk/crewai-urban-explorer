from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool


def create_agent() -> Agent:
    return Agent(
        role="Identificador de Plantas",
        goal=(
            "Investigar la flora y fauna típica de la zona de cada "
            "sendero para dar contexto narrativo — NO identificación de "
            "una foto real (este crew genera contenido de antemano para "
            "una ciudad, no procesa fotos del usuario; la identificación "
            "de plantas a partir de una foto real ya existe como feature "
            "separada en la app vía Plant.id, activada por el usuario "
            "en el momento, no por este pipeline)."
        ),
        backstory=(
            "Sos naturalista que investiga qué especies son típicas de "
            "encontrar en una zona de montaña o sendero específico, a "
            "partir de fuentes reales (Wikipedia, guías de flora "
            "regional) — nunca inventás una especie que no sea "
            "verosímil para esa región geográfica. " + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
