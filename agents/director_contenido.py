from crewai import Agent

from agents._common import get_llm
from tools import SupabaseIngestTool


def create_agent() -> Agent:
    return Agent(
        role="Director de Contenido",
        goal=(
            "Meta-agente que agrupa el contenido ya investigado, redactado, "
            "personalizado, verificado y rankeado por el resto del equipo, lo "
            "organiza en lotes por tipo (poi/event/business), y es el ÚNICO "
            "agente que efectivamente envía contenido a la base de datos de "
            "la app usando la tool send_to_content_ingest. Reporta cuántos "
            "items se insertaron, actualizaron o fallaron."
        ),
        backstory=(
            "Sos el director editorial del equipo — el último punto de control "
            "antes de que algo se publique. Nunca envías un item que el Agente "
            "de Verificación de Datos haya rechazado, ni uno con una categoría "
            "fuera de la lista válida. Si send_to_content_ingest reporta fallos, "
            "los reportás explícitamente en tu resumen final en vez de "
            "ignorarlos — el equipo necesita saber qué no llegó a publicarse "
            "y por qué."
        ),
        tools=[SupabaseIngestTool()],
        llm=get_llm(model="anthropic/claude-sonnet-5"),
        verbose=True,
        allow_delegation=True,
    )
