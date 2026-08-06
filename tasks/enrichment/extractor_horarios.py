from crewai import Agent, Task

from tasks._common import POI_JSON_SPEC, city_context


def create_task(
    agent: Agent, city: str, country: str, lat, lng, language: str,
    discovery_pois_json: str, discovery_businesses_json: str,
) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nPOIs de Discovery:\n" + discovery_pois_json
            + "\n\nNegocios de Discovery:\n" + discovery_businesses_json
            + "\n\nUsá overpass_poi_search para verificar la etiqueta "
            'opening_hours real de cada lugar y completar el campo '
            '"opening_hours" de los POIs cuando el dato exista en OSM. '
            "Si no hay dato real, dejá el campo vacío — nunca inventes un "
            "horario. Devolvé la lista completa de POIs."
        ),
        expected_output=POI_JSON_SPEC,
        agent=agent,
    )
