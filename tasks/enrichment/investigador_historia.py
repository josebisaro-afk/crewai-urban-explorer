from crewai import Agent, Task

from tasks._common import POI_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str, discovery_pois_json: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nEstos son los POIs que ya encontró el crew de Discovery:\n"
            f"{discovery_pois_json}\n\n"
            "Para los que tengan relevancia histórica real, agregales "
            'el campo "historical_period" (período histórico, si aplica) '
            "usando wikipedia_search para confirmarlo. Nunca inventes una "
            "fecha o período — si no está confirmado, dejá el campo vacío. "
            "Devolvé la lista completa (todos los POIs, no solo los que "
            "modificaste), con los demás campos sin cambios."
        ),
        expected_output=POI_JSON_SPEC,
        agent=agent,
    )
