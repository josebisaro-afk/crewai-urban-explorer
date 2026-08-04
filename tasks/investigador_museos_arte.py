from crewai import Agent, Task

from tasks._common import POI_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá wikipedia_search y overpass_poi_search (tags como "
            "tourism=museum, tourism=gallery, tourism=artwork) para encontrar "
            "hasta 6 museos o galerías relevantes, categoría museum, art o "
            "exhibition. Solo incluí lugares con coordenadas verificadas."
        ),
        expected_output=POI_JSON_SPEC,
        agent=agent,
    )
