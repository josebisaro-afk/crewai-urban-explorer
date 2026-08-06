from crewai import Agent, Task

from tasks._common import POI_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá wikipedia_search (mode='geosearch') y overpass_poi_search "
            "para encontrar rápido hasta 15 POIs evidentes (monumentos, "
            "museos, iglesias, parques, miradores) con coordenadas "
            "verificadas. No profundices en descripciones — solo nombre, "
            "categoría y coordenadas. Esto tiene que ser rápido: es lo "
            "primero que ve el usuario en el mapa."
        ),
        expected_output=POI_JSON_SPEC,
        agent=agent,
    )
