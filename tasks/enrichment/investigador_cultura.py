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
            + "\n\nUsá wikipedia_search para agregar contexto cultural "
            'real (tradiciones, identidad local) al campo "fun_fact" de '
            "los POIs que lo ameriten. No inventes tradiciones — solo lo "
            "que puedas confirmar. Devolvé la lista completa de POIs "
            "(todos, no solo los que modificaste)."
        ),
        expected_output=POI_JSON_SPEC,
        agent=agent,
    )
