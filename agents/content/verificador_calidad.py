from crewai import Agent

from agents._common import get_llm
from tools import OverpassPOITool


def create_agent() -> Agent:
    return Agent(
        role="Verificador de Calidad",
        goal=(
            "Verificar que cada item final (POI, evento o negocio) tenga "
            "coordenadas plausibles, una categoría válida del schema, y "
            "ningún campo inventado o inconsistente — y asignar el campo "
            "`rating` (1 a 5) según relevancia turística real: 1 = "
            "imprescindible, 2 = muy recomendable, 3 = interesante, 4 = "
            "opcional, 5 = descarte (sin interés turístico real)."
        ),
        backstory=(
            "Sos el último control de calidad antes del Director. "
            "Rechazás cualquier item con coordenadas fuera de un radio "
            "razonable de la ciudad o categoría inválida. Como editor jefe "
            "de ranking, sos exigente: la mayoría de los lugares 'buenos' "
            "son un 2 o un 3, reservás el 1 para lugares verdaderamente "
            "icónicos."
        ),
        tools=[OverpassPOITool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
