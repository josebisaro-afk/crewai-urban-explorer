from crewai import Agent, Task

from tasks._common import city_context


def create_task(
    agent: Agent, city: str, country: str, lat, lng, language: str,
    content_output: str, hiker_output: str = "",
) -> Task:
    hiker_block = f"\n\nContenido de Hiker Mode (rutas de senderismo):\n{hiker_output}" if hiker_output else ""
    return Task(
        description=(
            city_context(city, country, lat, lng, language)
            + "\nContenido final del crew de Content (POIs/eventos/"
            f"negocios ya redactados, verificados y traducidos):\n{content_output}"
            + hiker_block
            + "\n\nRevisá TODO este contenido antes de enviarlo. Rechazá "
            "(excluí del envío) cualquier item con: idioma inconsistente "
            "con target_language, categoría inválida, coordenadas "
            "implausibles, o información que se contradiga entre sí. "
            "Para cada tipo (poi/event/business) con al menos un item "
            "aprobado, agrupá esos items y llamá a la tool "
            "send_to_content_ingest UNA VEZ por tipo, con type correcto "
            "y todos los items aprobados de ese tipo juntos. No llames a "
            "la tool con listas vacías. Después de enviar, escribí un "
            "resumen final en target_language con cuántos items se "
            "insertaron/actualizaron/fallaron por tipo, y qué items "
            "rechazaste vos mismo antes de enviar (y por qué) para que "
            "puedan re-encolarse a los crews correspondientes en una "
            "corrida futura."
        ),
        expected_output=(
            f"Un resumen en texto plano del resultado del envío de "
            f"contenido para {city}: insertados/actualizados/fallidos "
            "por tipo, más los items rechazados por el propio Director "
            "antes de enviar y el motivo del rechazo."
        ),
        agent=agent,
    )
