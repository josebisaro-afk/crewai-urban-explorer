from crewai import Agent

from agents._common import get_llm
from tools import WeatherContextTool


def create_agent() -> Agent:
    return Agent(
        role="Clima y Contexto",
        goal=(
            "Consultar el clima actual de la ciudad para dar contexto "
            "práctico inmediato (temperatura, si conviene llevar agua o "
            "abrigo, si hay lluvia) que el resto del equipo y la app "
            "puedan usar de inmediato."
        ),
        backstory=(
            "Sos el meteorólogo del equipo. Tu único trabajo es consultar "
            "datos reales de clima con tu tool y resumirlos en una frase "
            "práctica y breve — nunca inventás condiciones climáticas."
        ),
        tools=[WeatherContextTool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
