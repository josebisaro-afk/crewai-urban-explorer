from crewai import Agent, Task

from tasks._common import POI_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá wikipedia_search y overpass_poi_search (tags como "
            "amenity=place_of_worship, building=church, building=cathedral) "
            "para encontrar hasta 6 templos de relevancia histórica o "
            "arquitectónica, categoría church. Solo incluí lugares con "
            "coordenadas verificadas."
        ),
        expected_output=POI_JSON_SPEC,
        agent=agent,
    )
