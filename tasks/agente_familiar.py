from crewai import Agent, Task

from tasks._common import POI_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá overpass_poi_search (tags como leisure=playground, "
            "tourism=theme_park, amenity=planetarium) para encontrar hasta 4 "
            "lugares adecuados para viajar con niños, categoría family."
        ),
        expected_output=POI_JSON_SPEC,
        agent=agent,
    )
