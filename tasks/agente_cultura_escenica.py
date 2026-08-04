from crewai import Agent, Task

from tasks._common import POI_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá overpass_poi_search (tags como amenity=theatre, "
            "amenity=cinema) y wikipedia_search para encontrar hasta 5 "
            "teatros, salas de flamenco/danza o cines con tradición real, "
            "categoría theatre, flamenco o cinema."
        ),
        expected_output=POI_JSON_SPEC,
        agent=agent,
    )
