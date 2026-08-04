from crewai import Agent, Task

from tasks._common import POI_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá overpass_poi_search (tags como amenity=restaurant, "
            "amenity=marketplace) y wikipedia_search (platos típicos de la "
            "región) para encontrar hasta 6 restaurantes o mercados con "
            "identidad culinaria local real, categoría gastronomy, "
            "restaurant o market."
        ),
        expected_output=POI_JSON_SPEC,
        agent=agent,
    )
