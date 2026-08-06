from crewai import Agent, Task

from tasks._common import city_context


def create_task(
    agent: Agent, city: str, country: str, lat, lng, language: str,
    discovery_output: dict, enrichment_output: dict,
) -> Task:
    combined = "\n\n".join(
        f"--- {key} ---\n{value}" for key, value in {**discovery_output, **enrichment_output}.items()
    )
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nTodo lo investigado por Discovery y Enrichment hasta "
            f"ahora:\n{combined}\n\n"
            "Convertí este material en descripciones narrativas finales, "
            "atractivas y bien escritas para POIs, eventos y negocios — "
            "sin inventar ningún dato que no venga del material de "
            "origen. Consolidá todo en un único array JSON de items, "
            'cada uno con un campo "type": "poi" | "event" | "business" '
            "además de los campos correspondientes a ese tipo."
        ),
        expected_output=(
            "Un array JSON único con todos los items (POIs, eventos, "
            'negocios) ya redactados, cada uno con "type" y sus campos '
            "correspondientes. Solo JSON, sin texto adicional."
        ),
        agent=agent,
    )
