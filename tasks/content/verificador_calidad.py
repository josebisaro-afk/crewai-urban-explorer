from crewai import Agent, Task

from config import VALID_CATEGORIES
from tasks._common import city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str, context: list[Task]) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nRevisá cada item del contexto. Usá overpass_poi_search "
            "para re-verificar coordenadas dudosas. RECHAZÁ (eliminá del "
            "array) cualquier item con coordenadas fuera de un radio "
            f"razonable (~15km) del centro de la ciudad, con categoría "
            f"fuera de esta lista válida: {sorted(VALID_CATEGORIES)}, o "
            "con campos obligatorios faltantes para su tipo. Para los "
            'POIs que pasen la verificación, asigná el campo "rating" (1 '
            "a 5): 1 = imprescindible, 2 = muy recomendable, 3 = "
            "interesante, 4 = opcional, 5 = descarte. Sé exigente — la "
            "mayoría son un 2 o un 3."
        ),
        expected_output="El array JSON filtrado y con rating asignado a cada POI. Solo JSON.",
        agent=agent,
        context=context,
    )
