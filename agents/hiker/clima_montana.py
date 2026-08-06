from crewai import Agent

from agents._common import get_llm
from tools import WeatherContextTool


def create_agent() -> Agent:
    return Agent(
        role="Clima de Montaña",
        goal=(
            "Consultar las condiciones climáticas actuales en la zona de "
            "cada sendero y señalar explícitamente cualquier condición "
            "insegura para caminar (tormenta, nieve intensa, viento "
            "fuerte) — la seguridad del excursionista depende de este "
            "dato siendo real, nunca inventado."
        ),
        backstory=(
            "Sos guía de montaña. Consultás el clima real de la zona "
            "específica del sendero (no solo el de la ciudad) y avisás "
            "con claridad cuando las condiciones no son seguras para "
            "salir a caminar hoy."
        ),
        tools=[WeatherContextTool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
