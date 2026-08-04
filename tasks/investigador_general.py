from crewai import Agent, Task

from tasks._common import city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nInvestigá el contexto general de esta ciudad: historia resumida "
            "en 3-4 frases, identidad cultural, y qué la distingue de otras "
            "ciudades de la región. Este contexto lo van a usar TODOS los "
            "agentes especialistas que vienen después, así que priorizá "
            "precisión sobre extensión."
        ),
        expected_output=(
            "Un resumen en texto plano (no JSON) de 150-250 palabras con el "
            "contexto histórico y cultural de la ciudad, en target_language."
        ),
        agent=agent,
    )
