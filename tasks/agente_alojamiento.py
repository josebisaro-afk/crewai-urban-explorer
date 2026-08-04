from crewai import Agent, Task

from tasks._common import POI_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá overpass_poi_search (tags como tourism=hotel) para "
            "encontrar hasta 4 hoteles con ubicación o carácter arquitectónico "
            "notable, categoría hotel."
        ),
        expected_output=POI_JSON_SPEC,
        agent=agent,
    )
