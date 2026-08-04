from crewai import Agent, Task

from tasks._common import POI_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nUsá overpass_poi_search (tags como tourism=picnic_site, "
            "information=trailhead, natural=peak) y wikipedia_search para "
            "encontrar hasta 4 puntos de partida de senderos o miradores de "
            "montaña cerca de la ciudad, categoría route. No generes rutas "
            "completas — eso lo hace otro sistema (hiking-routes) con datos "
            "de Overpass en tiempo real; tu trabajo es solo señalar POIs de "
            "referencia."
        ),
        expected_output=POI_JSON_SPEC,
        agent=agent,
    )
