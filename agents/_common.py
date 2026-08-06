"""Shared LLM instances for all 22 agents — kept in one place so the model
can be changed once instead of in 22 files. Uses the same ANTHROPIC_API_KEY
Supabase secret the app's own edge functions (chat, hiking-routes) already
use.

Two different integrations on purpose:
  - get_llm(): crewai's own LLM class (routes through litellm), used for the
    16 research agents on Haiku 4.5 — confirmed clean across two full runs.
  - get_chat_anthropic_llm(): langchain-anthropic's ChatAnthropic, talking to
    the Anthropic API directly instead of through litellm's routing/message
    formatting. claude-sonnet-5 and claude-opus-5 both hit a litellm-side
    "This model does not support assistant message prefill" error in every
    tool-calling loop (confirmed across multiple live runs, on the latest
    litellm release, on both models) — going around litellm entirely for
    these two models is the fix being tried here.
"""
from crewai import LLM
from langchain_anthropic import ChatAnthropic

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
    # across two full production runs.
    return LLM(model=model, api_key=ANTHROPIC_API_KEY)


def get_chat_anthropic_llm(model: str) -> ChatAnthropic:
    # For claude-sonnet-5 (Redactor, Personalizador, Agente de Idioma,
    # Verificación de Datos, Calidad y Ranking) and claude-opus-5 (Director
    # de Contenido) — bypasses litellm entirely by talking to the Anthropic
    # API directly through langchain-anthropic, since litellm's own message
    # formatting was the thing producing the invalid "assistant message
    # prefill" request for both of these models.
    return ChatAnthropic(model=model, api_key=ANTHROPIC_API_KEY)
