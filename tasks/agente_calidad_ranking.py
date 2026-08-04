from crewai import Agent, Task

from tasks._common import city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str, context: list[Task]) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nTomá los items JSON ya verificados (ver contexto). Para cada "
            'POI, asigná el campo "rating" (1 a 5): 1 = imprescindible, 2 = '
            "muy recomendable, 3 = interesante, 4 = opcional, 5 = descarte. "
            "Sé exigente — la mayoría de los lugares buenos son un 2 o un 3, "
            "reservá el 1 para lugares verdaderamente icónicos de la ciudad. "
            "Los eventos y negocios no necesitan rating. Devolvé la lista "
            "completa."
        ),
        expected_output="El mismo array JSON, con rating asignado a cada POI. Solo JSON.",
        agent=agent,
        context=context,
    )
