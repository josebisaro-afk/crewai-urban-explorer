from crewai import Agent

from agents._common import get_llm
from tools import OverpassPOITool


def create_agent() -> Agent:
    return Agent(
        role="Extractor de Horarios",
        goal=(
            "Verificar horarios de apertura reales de los POIs y negocios "
            "ya encontrados, usando datos de OpenStreetMap (etiqueta "
            "opening_hours) cuando estén disponibles. Nunca inventa un "
            "horario — si no hay dato real, lo deja en blanco."
        ),
        backstory=(
            "Sos el que se asegura de que nadie llegue a un museo cerrado. "
            "Trabajás solo con datos verificables de OSM; si Overpass no "
            "tiene el dato, preferís dejarlo vacío a adivinar un horario "
            "típico que podría estar mal."
        ),
        tools=[OverpassPOITool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
