from crewai import Agent, Task

from tasks._common import city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str, context: list[Task]) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nTomá los items ya redactados (ver contexto) y, para cada "
            'POI, agregá cuando corresponda: "fun_fact" (dato curioso '
            'real, no inventado) y "accessibility_info" (si hay '
            "información real disponible). No agregues campos que el "
            "schema no soporta. Devolvé la lista completa."
        ),
        expected_output="El mismo array JSON, con enriquecimientos agregados donde corresponda. Solo JSON.",
        agent=agent,
        context=context,
    )
