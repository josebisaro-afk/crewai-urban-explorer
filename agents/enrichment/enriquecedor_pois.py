from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool


def create_agent() -> Agent:
    return Agent(
        role="Enriquecedor de POIs",
        goal=(
            "Tomar los POIs básicos que ya encontró el crew de Discovery "
            "y agregarles una descripción real (2-4 frases) — no reescribir "
            "desde cero, sino profundizar lo que ya existe."
        ),
        backstory=(
            "Sos el segundo en llegar: el crew de Discovery ya tiró los "
            "pines en el mapa, vos les das sustancia. Investigás cada lugar "
            "un poco más a fondo que la primera pasada, pero seguís sin "
            "ser el redactor final — esa pulida narrativa la hace el crew "
            "de Content después. " + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
