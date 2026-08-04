from crewai import Agent, Task

from tasks._common import EVENT_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá wikipedia_search (mode='search' con términos como "
            "'festival [ciudad]', 'feria anual [ciudad]') para encontrar hasta "
            "4 festivales o eventos recurrentes con fecha confirmable, "
            "categoría concert o festival. Si no podés confirmar la fecha "
            "real del próximo evento, NO lo incluyas."
        ),
        expected_output=EVENT_JSON_SPEC,
        agent=agent,
    )
