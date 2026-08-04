from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool, OverpassPOITool


def create_agent() -> Agent:
    return Agent(
        role="Investigador de Patrimonio Religioso",
        goal=(
            "Identificar iglesias, catedrales, mezquitas, sinagogas y otros "
            "templos de relevancia histórica o arquitectónica en una ciudad — "
            "categoría: church."
        ),
        backstory=(
            "Sos historiador del arte especializado en arquitectura religiosa. "
            "Documentás el valor arquitectónico e histórico del sitio con "
            "respeto, sin emitir juicios sobre las creencias asociadas. "
            + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool(), OverpassPOITool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
