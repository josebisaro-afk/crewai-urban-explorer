from crewai import Agent, Task

from tasks._common import ROUTE_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str, context: list[Task]) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nTomá los items finales del contexto (ya traducidos y "
            "verificados) y agrupá los POIs (type=\"poi\") en 2-3 rutas "
            "temáticas con sentido. Usá solo POIs que ya están en el "
            "contexto — no inventes lugares nuevos."
        ),
        expected_output=ROUTE_JSON_SPEC,
        agent=agent,
        context=context,
    )
