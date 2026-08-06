from crewai import Agent, Task

from tasks._common import EVENT_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá wikipedia_search (mode='search') para encontrar rápido "
            "hasta 3 festivales o eventos recurrentes con fecha "
            "confirmable. Solo título, categoría y fecha — sin desarrollar "
            "la descripción todavía."
        ),
        expected_output=EVENT_JSON_SPEC,
        agent=agent,
    )
