from crewai import Agent, Task

from tasks._common import city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str, context: list[Task]) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nTomá los items JSON (POIs y eventos) que produjeron los "
            "agentes investigadores en las tareas anteriores (ver contexto) y "
            "redactá una descripción narrativa atractiva para cada uno — "
            'campo "description_es" para POIs si target_language es "es" (o '
            '"description_en" si es otro idioma — el schema de la app solo '
            "tiene esos dos slots de idioma, así que un idioma que no sea "
            "español va en description_en), o \"description\" para eventos. "
            "NO inventes ningún dato (fecha, cifra, nombre) que no venga del "
            "material de investigación. Mantené todos los demás campos del "
            "item sin modificar y devolvé la lista completa."
        ),
        expected_output=(
            "El mismo array JSON de items recibido, con las descripciones "
            "narrativas ya redactadas en target_language. Solo JSON, sin "
            "texto adicional."
        ),
        agent=agent,
        context=context,
    )
