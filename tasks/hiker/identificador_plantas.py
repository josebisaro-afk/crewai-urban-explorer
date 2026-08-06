from crewai import Agent, Task

from tasks._common import city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str, context: list[Task]) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nPara la zona de los senderos verificados del contexto, "
            "usá wikipedia_search para investigar flora y fauna típica de "
            "la región. No inventes especies no verosímiles para esa zona "
            "geográfica."
        ),
        expected_output=(
            "Texto plano (no JSON) describiendo flora y fauna típica de "
            "la zona, en target_language."
        ),
        agent=agent,
        context=context,
    )
