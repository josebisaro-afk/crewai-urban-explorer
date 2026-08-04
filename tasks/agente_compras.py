from crewai import Agent, Task

from tasks._common import POI_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá overpass_poi_search (tags como shop=gift, shop=craft, "
            "shop=marketplace) para encontrar hasta 5 tiendas o mercados con "
            "identidad local (artesanía, productos típicos), categoría shop."
        ),
        expected_output=POI_JSON_SPEC,
        agent=agent,
    )
