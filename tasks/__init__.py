"""Mirrors agents/__init__.py's AGENT_MODULES — one task-factory module per
agent, same key and same order, so crew.py can zip them together.
"""
from tasks import (
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

# Research/writer tasks that need no `context` (they call tools directly).
RESEARCH_TASK_MODULES = [
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
]

# Pipeline tasks that each depend on the previous one's output (context=[...]),
# run strictly in this order after all research tasks complete.
PIPELINE_TASK_MODULES = [
    ("agente_redactor", agente_redactor),
    ("personalizador", personalizador),
    ("agente_idioma", agente_idioma),
    ("agente_verificacion_datos", agente_verificacion_datos),
    ("agente_calidad_ranking", agente_calidad_ranking),
    ("director_contenido", director_contenido),
]

assert len(RESEARCH_TASK_MODULES) + len(PIPELINE_TASK_MODULES) == 22
