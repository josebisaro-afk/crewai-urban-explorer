from crewai import Agent, Task

from tasks._common import POI_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá wikipedia_search (mode='geosearch' con las coordenadas del "
            "centro) y overpass_poi_search (tags como historic=monument, "
            "historic=castle, historic=archaeological_site, tourism=monument) "
            "para encontrar hasta 8 monumentos, sitios históricos o ejemplos de "
            "arquitectura notable con categoría monument, history o "
            "architecture. Solo incluí lugares con coordenadas verificadas por "
            "una tool."
        ),
        expected_output=POI_JSON_SPEC,
        agent=agent,
    )
