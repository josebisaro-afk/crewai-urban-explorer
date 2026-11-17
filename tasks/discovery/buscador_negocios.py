from crewai import Agent, Task

from tasks._common import BUSINESS_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá overpass_poi_search para encontrar negocios REALES con "
            "identidad local. Prioridad 1: entre 8 y 15 sitios para comer y "
            "beber (amenity=restaurant, amenity=cafe, amenity=bar, "
            "amenity=pub, y bodegas/catas: craft=winery, shop=wine) — "
            "category \"restaurant\" para restaurantes y cafés, \"bar\" "
            "para bares, pubs y bodegas. Prioridad 2: hasta 5 alojamientos "
            "o tiendas típicas (tourism=hotel, shop=*). Para restaurantes y "
            "bares lat y lng son OBLIGATORIOS y deben salir de la tool; si "
            "un sitio no tiene coordenadas, no lo incluyas. Incluí address "
            "si la tool lo da. No inventes nada."
        ),
        expected_output=BUSINESS_JSON_SPEC,
        agent=agent,
    )
