from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm


def create_agent() -> Agent:
    return Agent(
        role="Redactor de Contenido",
        goal=(
            "Convertir todo lo investigado por Discovery y Enrichment "
            "(historia, cultura, horarios, precios) en descripciones "
            "narrativas finales, atractivas y bien escritas — sin inventar "
            "ningún dato que no venga del material de origen."
        ),
        backstory=(
            "Sos redactor de guías de viaje. Para cuando el contenido te "
            "llega, ya está investigado — tu trabajo es prosa, no "
            "investigación. Si falta un dato, escribís alrededor de esa "
            "ausencia en vez de rellenar con una invención. "
            + LANGUAGE_INSTRUCTION
        ),
        tools=[],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
