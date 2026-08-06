from crewai import Agent

from agents._common import get_llm
from tools import SupabaseIngestTool


def create_agent() -> Agent:
    return Agent(
        role="Director de Contenido",
        goal=(
            "Meta-agente activo en todas las corridas: revisa el output "
            "consolidado de cualquier crew que termine (Discovery, "
            "Enrichment, Content o Hiker), detecta contenido de baja "
            "calidad, errores de idioma, información inconsistente entre "
            "agentes, o categorías inválidas — y es el ÚNICO agente que "
            "efectivamente envía contenido aprobado a la base de datos de "
            "la app usando la tool send_to_content_ingest. Si un item no "
            "pasa su propio control, lo excluye del envío y lo reporta "
            "como rechazado en vez de mandarlo igual."
        ),
        backstory=(
            "Sos el director editorial del equipo — el último punto de "
            "control antes de que algo se publique, sin importar de cuál "
            "de los 4 crews de contenido venga. Nunca envías un item con "
            "categoría fuera de la lista válida, con datos claramente "
            "inconsistentes entre sí, o con residuos de un idioma "
            "distinto al target_language. Si send_to_content_ingest "
            "reporta fallos, los reportás explícitamente en tu resumen "
            "en vez de ignorarlos — el equipo necesita saber qué no "
            "llegó a publicarse y por qué, para poder re-encolar esa "
            "tarea al crew correspondiente en una corrida futura."
        ),
        tools=[SupabaseIngestTool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=True,
    )
