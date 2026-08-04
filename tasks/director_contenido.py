from crewai import Agent, Task

from tasks._common import city_context


def create_task(agent: Agent, city: str, country: str, lat, lng, language: str, context: list[Task]) -> Task:
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nSos el último paso del pipeline. Tomá TODOS los items JSON "
            "producidos en el contexto (POIs verificados y rankeados, más "
            "eventos) y agrupalos en lotes por tipo. Para cada lote no "
            'vacío, llamá a la tool send_to_content_ingest UNA VEZ con type='
            '"poi" y todos los items POI juntos, y otra vez con type="event" '
            "si hay eventos. No llames a la tool con listas vacías. Después "
            "de llamar a la tool, escribí un resumen final en target_language "
            "con cuántos items se insertaron, actualizaron o fallaron para "
            f"{city}, citando cualquier error reportado por la tool."
        ),
        expected_output=(
            f"Un resumen en texto plano del resultado del envío de contenido "
            f"para {city}: cuántos POIs y eventos se insertaron/actualizaron/"
            "fallaron, y el detalle de cualquier fallo."
        ),
        agent=agent,
        context=context,
    )
