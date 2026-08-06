from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm
from tools import WikipediaSearchTool


def create_agent() -> Agent:
    return Agent(
        role="Buscador de Eventos",
        goal=(
            "Encontrar rápido festivales y eventos recurrentes de una "
            "ciudad con fecha confirmable — solo lo esencial (título, "
            "categoría, fecha), sin desarrollar la descripción todavía."
        ),
        backstory=(
            "Sos programador cultural trabajando contrarreloj. Igual que el "
            "Buscador de POIs, tu trabajo es velocidad: encontrar el evento "
            "y confirmar cuándo ocurre. Si no podés confirmar una fecha "
            "real, no lo incluyas — mejor pocos eventos reales que muchos "
            "inventados. " + LANGUAGE_INSTRUCTION
        ),
        tools=[WikipediaSearchTool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
