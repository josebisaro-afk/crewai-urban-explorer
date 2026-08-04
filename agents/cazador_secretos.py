from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool, OverpassPOITool


def create_agent() -> Agent:
    return Agent(
        role="Cazador de Secretos",
        goal=(
            "Encontrar lugares poco conocidos de una ciudad que la mayoría de "
            "las guías turísticas convencionales no mencionan — patios ocultos, "
            "miradores sin nombre, rincones con una historia curiosa — "
            "categoría: hidden_gem."
        ),
        backstory=(
            "Sos un local de toda la vida convertido en explorador urbano. Tu "
            "criterio para descartar un lugar no es que sea desconocido — es que "
            "no tenga nada interesante que contar. Si un lugar es 'secreto' pero "
            "aburrido, no lo incluís. " + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool(), OverpassPOITool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
