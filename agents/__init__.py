"""Registry of all 22 agents (21 specialists + 1 Director meta-agent) so
crew.py and the admin UI can enumerate them without importing each module
by hand. Order matters for crew.py's sequential process: research agents
first, then writing/QA, then the Director last.
"""
from agents import (
    investigador_general,
    investigador_historico,
    investigador_museos_arte,
    investigador_religioso,
    investigador_naturaleza,
    cazador_secretos,
    agente_senderista,
    agente_gastronomia,
    agente_vida_nocturna,
    agente_alojamiento,
    agente_compras,
    agente_experiencias_tours,
    agente_eventos_conciertos,
    agente_cultura_escenica,
    agente_deportivo,
    agente_familiar,
    agente_redactor,
    personalizador,
    agente_idioma,
    agente_verificacion_datos,
    agente_calidad_ranking,
    director_contenido,
)

# (key, module) — key is used to look up the matching module in tasks/__init__.py
AGENT_MODULES = [
    ("investigador_general", investigador_general),
    ("investigador_historico", investigador_historico),
    ("investigador_museos_arte", investigador_museos_arte),
    ("investigador_religioso", investigador_religioso),
    ("investigador_naturaleza", investigador_naturaleza),
    ("cazador_secretos", cazador_secretos),
    ("agente_senderista", agente_senderista),
    ("agente_gastronomia", agente_gastronomia),
    ("agente_vida_nocturna", agente_vida_nocturna),
    ("agente_alojamiento", agente_alojamiento),
    ("agente_compras", agente_compras),
    ("agente_experiencias_tours", agente_experiencias_tours),
    ("agente_eventos_conciertos", agente_eventos_conciertos),
    ("agente_cultura_escenica", agente_cultura_escenica),
    ("agente_deportivo", agente_deportivo),
    ("agente_familiar", agente_familiar),
    ("agente_redactor", agente_redactor),
    ("personalizador", personalizador),
    ("agente_idioma", agente_idioma),
    ("agente_verificacion_datos", agente_verificacion_datos),
    ("agente_calidad_ranking", agente_calidad_ranking),
    ("director_contenido", director_contenido),
]

assert len(AGENT_MODULES) == 22, "Expected exactly 22 agents (21 specialists + 1 Director)"
