from crewai import Agent, Task

from tasks._common import POI_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá overpass_poi_search (tags como leisure=stadium, "
            "sport=*) y wikipedia_search para encontrar hasta 3 instalaciones "
            "o actividades deportivas de interés turístico real, categoría "
            "sport."
        ),
        expected_output=POI_JSON_SPEC,
        agent=agent,
    )
