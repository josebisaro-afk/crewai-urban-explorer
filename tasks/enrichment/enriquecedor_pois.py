from crewai import Agent, Task

from tasks._common import POI_JSON_SPEC, city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str, discovery_pois_json: str) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nEstos son los POIs que ya encontró el crew de Discovery "
            f"(otra corrida, ya terminada):\n{discovery_pois_json}\n\n"
            "Tomá esta lista y agregale a cada item una descripción real "
            "de 2-4 frases (campo description_es o description_en según "
            "target_language) usando wikipedia_search para profundizar. "
            "No inventes POIs nuevos — solo enriquecé los que ya están en "
            "la lista. Mantené todos los demás campos (city, name, "
            "category, lat, lng) exactamente igual."
        ),
        expected_output=POI_JSON_SPEC,
        agent=agent,
    )
