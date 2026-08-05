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


def get_llm(model: str = "anthropic/claude-opus-5") -> LLM:
    # `temperature` is rejected outright by the Anthropic API for claude-sonnet-5
    # ("`temperature` is deprecated for this model") — confirmed in production
    # via a live crew run, where it made every single agent call fail with a
    # 400 before any content could be generated. Omit it; the model's default
    # sampling is used instead.
    #
    # claude-sonnet-5 also throws a second, separate error in every one of
    # this crew's tool-calling loops — "This model does not support assistant
    # message prefill. The conversation must end with a user message." —
    # confirmed still present after upgrading litellm to the latest release
    # (not a stale-litellm issue). Switching only the 21 non-Director agents
    # to Haiku 4.5 confirmed it too: all 21 completed clean with no prefill
    # errors, and the run only failed at the very last step, where
    # director_contenido.py had been deliberately kept on claude-sonnet-5 and
    # hit the identical error the moment it called send_to_content_ingest —
    # pinning this squarely on claude-sonnet-5 + tool calls, not litellm
    # version or the research agents' prompts. Every agent (including the
    # Director) now uses claude-opus-5 instead.
    return LLM(model=model, api_key=ANTHROPIC_API_KEY)
