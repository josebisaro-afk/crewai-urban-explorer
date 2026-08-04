from crewai import Agent, Task

from tasks._common import POI_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá wikipedia_search y overpass_poi_search (tags como "
            "leisure=park, leisure=garden, tourism=viewpoint, "
            "boundary=national_park) para encontrar hasta 6 parques, jardines "
            "o miradores accesibles, categoría park, nature o viewpoint. Solo "
            "incluí lugares con coordenadas verificadas."
        ),
        expected_output=POI_JSON_SPEC,
        agent=agent,
    )
