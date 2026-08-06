from crewai import Agent, Task

from tasks._common import BUSINESS_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá overpass_poi_search (tags como amenity=restaurant, "
            "amenity=bar, tourism=hotel, shop=*) para encontrar rápido "
            "hasta 10 negocios con identidad local. Solo nombre, categoría "
            "y coordenadas cuando estén disponibles."
        ),
        expected_output=BUSINESS_JSON_SPEC,
        agent=agent,
    )
