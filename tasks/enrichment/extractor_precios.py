from crewai import Agent, Task

from tasks._common import city_context


def create_task(
    agent: Agent, city: str, country: str, lat, lng, language: str,
    discovery_businesses_json: str,
) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nNegocios de Discovery:\n" + discovery_businesses_json
            + "\n\nUsá overpass_poi_search para buscar etiquetas de precio "
            "reales (fee, charge) cuando existan. Nunca inventes una "
            "cifra exacta — cuando no hay dato real, indicá un nivel "
            "general (gratuito / económico / no disponible)."
        ),
        expected_output=(
            "Un resumen en texto plano (no JSON) con notas de precio por "
            "negocio, solo para los que tengan dato real o nivel general "
            "estimable, en target_language."
        ),
        agent=agent,
    )
