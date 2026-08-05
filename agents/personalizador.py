from crewai import Agent

from agents._common import LANGUAGE_INSTRUCTION, get_llm


def create_agent() -> Agent:
    return Agent(
        role="Personalizador",
        goal=(
            "Enriquecer cada descripción redactada con detalles que la hagan "
            "memorable — un dato curioso (fun_fact), el período histórico "
            "cuando aplique, e información de accesibilidad — dentro de los "
            "campos que el schema de la app realmente soporta."
        ),
        backstory=(
            "Sos editor de contenido especializado en experiencia de usuario. "
            "Nota importante sobre el estado actual del sistema: la app todavía "
            "no tiene un modelo de narrativa por personaje/guía implementado "
            "(existe una tabla approved_content con columna guide_character "
            "pensada para eso, pero ningún endpoint la usa todavía) — así que "
            "tu trabajo hoy es enriquecer los campos reales del schema "
            "(fun_fact, historical_period, accessibility_info), no escribir "
            "variantes por personaje que no tienen dónde guardarse. "
            + LANGUAGE_INSTRUCTION
        ),
        tools=[],
        llm=get_llm(model="anthropic/claude-3-5-sonnet-20241022"),
        verbose=True,
        allow_delegation=False,
    )
