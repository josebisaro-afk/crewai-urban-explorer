from crewai import Agent, Task

from tasks._common import city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str, context: list[Task]) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nRevisá los senderos del contexto. RECHAZÁ cualquiera con "
            "coordenadas fuera de un radio razonable (~30km) de la ciudad, "
            "o sin coordenadas de partida válidas."
        ),
        expected_output="El mismo array JSON, filtrado a solo los senderos verificados. Solo JSON.",
        agent=agent,
        context=context,
    )
