from crewai import Agent, Task

from tasks._common import POI_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá wikipedia_search y overpass_poi_search (tags como "
            "tourism=attraction) para encontrar hasta 4 experiencias o tours "
            "distintivos de la ciudad (clases, tours temáticos, actividades "
            "vivenciales), categoría experience o tour."
        ),
        expected_output=POI_JSON_SPEC,
        agent=agent,
    )
