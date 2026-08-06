from crewai import Agent, Task

from tasks._common import city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str, context: list[Task]) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nCombiná los senderos verificados, el clima/condiciones y "
            "la flora/fauna del contexto en una narración final por "
            "sendero: historia y curiosidades, flora y fauna, y una nota "
            "práctica de condiciones. No inventes ningún dato nuevo."
        ),
        expected_output=(
            "Un array JSON de rutas de senderismo, cada una con \"name\", "
            "\"start_lat\", \"start_lng\", \"history_and_curiosities\", "
            "\"flora_fauna\", y \"conditions_note\". Solo JSON."
        ),
        agent=agent,
        context=context,
    )
