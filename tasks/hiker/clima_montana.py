from crewai import Agent, Task

from tasks._common import city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str, context: list[Task]) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nPara cada sendero verificado del contexto, usá "
            "weather_context con sus coordenadas de partida para chequear "
            "condiciones actuales. Señalá explícitamente cualquier "
            "condición insegura para caminar."
        ),
        expected_output=(
            "Texto plano (no JSON) con el clima y una nota de seguridad "
            "por sendero, en target_language."
        ),
        agent=agent,
        context=context,
    )
