"""Shared description/expected_output fragments so every task file (across
all 5 crews) states the city context and the required JSON shape
identically — keeps the task files consistent without repeating the same
paragraph with small drift.
"""


def city_context(city: str, country: str, lat: float | None, lng: float | None, language: str) -> str:
    coords = f"lat={lat}, lng={lng}" if lat is not None and lng is not None else "coordinates unknown, geocode the city centre first"
    return (
        f"Ciudad: {city}\nPaís: {country}\nCoordenadas del centro: {coords}\n"
        f"target_language: {language}\n"
    )


POI_JSON_SPEC = (
    "Devolvé un array JSON de objetos POI. Cada objeto DEBE tener exactamente "
    'estos campos (nombres exactos, en inglés): "city", "name", "category" '
    "(una de las categorías válidas), \"lat\", \"lng\" (obligatorios), y "
    'opcionalmente "country", "description_es", "description_en", "address", '
    '"opening_hours", "image_url", "historical_period", "fun_fact". No '
    "inventes coordenadas: si no las verificaste con una tool, no incluyas el "
    "item. Devolvé SOLO el JSON, sin texto adicional."
)

EVENT_JSON_SPEC = (
    "Devolvé un array JSON de objetos de evento. Cada objeto DEBE tener "
    'exactamente estos campos: "city", "title", "category", "date" (formato '
    'YYYY-MM-DD, obligatorios), y opcionalmente "country", "description", '
    '"venue", "address", "is_free". Si no podés confirmar una fecha real, NO '
    "incluyas ese evento. Devolvé SOLO el JSON, sin texto adicional."
)

BUSINESS_JSON_SPEC = (
    "Devolvé un array JSON de objetos de negocio. Cada objeto DEBE tener "
    'exactamente estos campos: "city", "name", "category" (obligatorios), y '
    'opcionalmente "country", "description", "address", "lat", "lng", '
    '"website". Devolvé SOLO el JSON, sin texto adicional.'
)

ROUTE_JSON_SPEC = (
    "Devolvé un array JSON de objetos de ruta temática (2-3 rutas). Cada "
    'objeto DEBE tener: "theme_name" (nombre de la ruta), "description" '
    '(1-2 frases del hilo conductor), "poi_names" (array de strings — '
    "nombres EXACTOS de POIs que ya existen en el contenido verificado del "
    "contexto, en el orden sugerido de visita). No inventes POIs que no "
    "estén ya en el contexto. Devolvé SOLO el JSON, sin texto adicional."
)
