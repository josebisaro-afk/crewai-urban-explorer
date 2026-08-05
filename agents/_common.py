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
    # not just Sonnet. Haiku 4.5 is the only model tested that does NOT hit
    # this: a full run with Haiku on the 21 non-Director agents completed all
    # of them with zero prefill errors, only failing at the final step where
    # director_contenido.py was still on Sonnet/Opus. Every agent, including
    # the Director, now defaults to Haiku 4.5.
    return LLM(model=model, api_key=ANTHROPIC_API_KEY)
