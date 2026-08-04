from crewai import Agent, Task

from tasks._common import city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str, context: list[Task]) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nTomá los items JSON ya redactados (ver contexto) y, para "
            'cada POI, agregá cuando corresponda: "fun_fact" (un dato curioso '
            'real, no inventado), "historical_period" (si aplica), y '
            '"accessibility_info" (si hay información real disponible — no '
            "inventes que un lugar es accesible si no lo verificaste). No "
            "agregues campos que el schema no soporta. Devolvé la lista "
            "completa con estos enriquecimientos."
        ),
        expected_output=(
            "El mismo array JSON, con fun_fact/historical_period/"
            "accessibility_info agregados donde corresponda. Solo JSON."
        ),
        agent=agent,
        context=context,
    )
