from crewai import Agent, Task

from tasks._common import city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá weather_context con las coordenadas del centro de la "
            "ciudad para obtener el clima real actual."
        ),
        expected_output=(
            "Un resumen en texto plano (no JSON), 1-2 frases, del clima "
            "actual y una nota práctica breve (ej. si conviene llevar "
            "agua o abrigo), en target_language."
        ),
        agent=agent,
    )
