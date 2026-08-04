from crewai import Agent, Task

from config import VALID_CATEGORIES
from tasks._common import city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str, context: list[Task]) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nRevisá cada item JSON del contexto. Usá overpass_poi_search "
            "para re-verificar coordenadas dudosas cuando lo necesites. "
            "RECHAZÁ (eliminá del array) cualquier item que cumpla alguna de "
            "estas condiciones: coordenadas fuera de un radio razonable "
            f"(~15km) del centro de la ciudad; categoría fuera de esta lista "
            f"válida: {sorted(VALID_CATEGORIES)}; falta algún campo "
            "obligatorio para su tipo (POI: city/name/category/lat/lng; "
            "evento: city/title/category/date; negocio: city/name/category). "
            "Devolvé solo los items aprobados."
        ),
        expected_output=(
            "El array JSON filtrado, solo con los items que pasaron la "
            "verificación. Solo JSON, sin explicación."
        ),
        agent=agent,
        context=context,
    )
