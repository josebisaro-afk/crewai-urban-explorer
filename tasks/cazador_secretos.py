from crewai import Agent, Task

from tasks._common import POI_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá wikipedia_search (mode='search' con términos como "
            "'rincones ocultos', historias curiosas locales) y "
            "overpass_poi_search para encontrar hasta 4 lugares poco "
            "conocidos con una historia curiosa real detrás, categoría "
            "hidden_gem. No incluyas un lugar solo porque es poco conocido — "
            "tiene que tener algo genuinamente interesante que contar."
        ),
        expected_output=POI_JSON_SPEC,
        agent=agent,
    )
