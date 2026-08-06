from crewai import Agent, Task

from tasks._common import city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá overpass_poi_search (tags como route=hiking, "
            "highway=path, highway=track) para encontrar hasta 5 senderos "
            "reales cerca de la ciudad, con coordenadas del punto de "
            "partida verificadas."
        ),
        expected_output=(
            "Un array JSON de senderos, cada uno con \"name\", \"start_lat\", "
            "\"start_lng\", y opcionalmente \"description\". Solo JSON."
        ),
        agent=agent,
    )
