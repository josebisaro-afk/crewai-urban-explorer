"""Shared LLM instance for all 22 agents — kept in one place so the model
can be changed once instead of in 22 files. Uses the same ANTHROPIC_API_KEY
Supabase secret the app's own edge functions (chat, hiking-routes) already
use, via LiteLLM's "anthropic/<model>" provider prefix that crewai.LLM expects.
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
    # `temperature` is rejected outright by the Anthropic API for claude-sonnet-5
    # ("`temperature` is deprecated for this model") — confirmed in production
    # via a live crew run, where it made every single agent call fail with a
    # 400 before any content could be generated. Omit it; the model's default
    # sampling is used instead.
    #
    # Both claude-sonnet-5 AND claude-opus-5 throw a second, separate error in
    # every one of this crew's tool-calling loops — "This model does not
    # support assistant message prefill. The conversation must end with a
    # user message." — confirmed on the latest litellm release (not a
    # stale-litellm issue), and confirmed on both "Claude 5 family" models,
    # not just Sonnet. Haiku 4.5 is the only model confirmed clean of this
    # bug across a full run, which is why it's the default here — used as-is
    # by the 16 research agents. The 6 writing/QA/director agents
    # (agente_redactor, personalizador, agente_idioma,
    # agente_verificacion_datos, agente_calidad_ranking,
    # director_contenido — all of whom either read a lot of upstream context
    # or, for the Director, call a tool) each explicitly override this to
    # claude-3-5-sonnet-20241022 instead, an older Sonnet generation that
    # predates whatever changed in the Claude 5 family's tool-calling
    # message-prefill validation.
    return LLM(model=model, api_key=ANTHROPIC_API_KEY)
