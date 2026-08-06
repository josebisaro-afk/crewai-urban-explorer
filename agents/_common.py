"""Shared LLM instance for all 22 agents — kept in one place so the model
can be changed once instead of in 22 files. Uses the same ANTHROPIC_API_KEY
Supabase secret the app's own edge functions (chat, hiking-routes) already
use, via LiteLLM's "anthropic/<model>" provider prefix that crewai.LLM expects.

Tried and abandoned: passing a raw langchain_anthropic.ChatAnthropic
instance as Agent(llm=...) to bypass litellm entirely. CrewAI 0.86.0
doesn't support that — it still funnels the object through its own
litellm-backed LLM class internally, and ends up passing litellm the
object's repr() as the "model" string ("LLM Provider NOT provided..."),
confirmed in a live run. Making that path work for real would need a
custom crewai.llms.base_llm.BaseLLM adapter, out of scope here.
"""
from crewai import LLM

from config import ANTHROPIC_API_KEY

LANGUAGE_INSTRUCTION = (
    "You must write ALL final content (names, descriptions, narratives) in the "
    "language given to you as `target_language` (an ISO 639-1 code) — never in "
    "any other language, even if your source material (Wikipedia, OSM tags) is "
    "in a different language. Research in whatever language returns the best "
    "results, but translate/write the final output in target_language."
)


def get_llm(model: str = "anthropic/claude-haiku-4-5-20251001") -> LLM:
    # Used as-is (Haiku 4.5, no override) by the 16 research agents — do not
    # change this without re-verifying: `temperature` used to be passed here
    # and is rejected outright by the Anthropic API for claude-sonnet-5, and
    # separately, claude-sonnet-5/claude-opus-5 both threw a litellm-side
    # "assistant message prefill" error in every tool-calling loop. Haiku 4.5
    # via this litellm-routed path has been confirmed clean of both issues
    # across two full production runs. The 6 writing/QA/Director agents
    # (agente_redactor, personalizador, agente_idioma,
    # agente_verificacion_datos, agente_calidad_ranking,
    # director_contenido) explicitly override this to
    # "anthropic/claude-sonnet-5" instead.
    return LLM(model=model, api_key=ANTHROPIC_API_KEY)
