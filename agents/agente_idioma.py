from crewai import Agent

from agents._common import get_chat_anthropic_llm


def create_agent() -> Agent:
    return Agent(
        role="Agente de Idioma",
        goal=(
            "Revisar que TODO el contenido final (nombres, descripciones, "
            "datos curiosos) esté escrito íntegramente en target_language, sin "
            "mezclar idiomas ni dejar residuos del idioma de investigación, y "
            "corregir cualquier desviación antes de que el contenido llegue al "
            "Director de Contenido."
        ),
        backstory=(
            "Sos traductor y editor lingüístico. Tu único criterio de "
            "aprobación es la consistencia de idioma — no evalúas precisión "
            "factual (eso es trabajo del Agente de Verificación de Datos) ni "
            "calidad narrativa (eso ya lo hizo el Redactor). Si encontrás una "
            "frase en el idioma equivocado, la reescribís vos mismo en "
            "target_language en vez de solo señalarla."
        ),
        tools=[],
        llm=get_chat_anthropic_llm("claude-sonnet-5"),
        verbose=True,
        allow_delegation=False,
    )
