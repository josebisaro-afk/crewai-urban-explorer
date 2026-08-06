"""Shared LLM instance for every agent across all 5 crews — kept in one
place so the model can be changed once instead of in ~20 files. Uses the
same ANTHROPIC_API_KEY Supabase secret the app's own edge functions (chat,
hiking-routes) already use, via LiteLLM's "anthropic/<model>" provider
prefix that crewai.LLM expects.

ALL agents currently use the default below (Haiku 4.5) — it's the only
model confirmed to work cleanly with this version of CrewAI/litellm. Both
claude-sonnet-5 and claude-opus-5 were tried for the old roster's 6
non-research agents across several attempts and consistently failed:
  - Via crewai.LLM/litellm ("anthropic/claude-sonnet-5" /
    "anthropic/claude-opus-5"): litellm.BadRequestError, "This model does
    not support assistant message prefill. The conversation must end with
    a user message." — in every tool-calling loop, on the latest litellm
    release (1.95.0), so not a stale-litellm issue.
  - Via langchain_anthropic.ChatAnthropic passed directly as Agent(llm=...)
    to bypass litellm: doesn't work either — CrewAI 0.86.0 still funnels
    the object through its own litellm-backed LLM class internally and
    passes litellm the object's repr() as "model" ("LLM Provider NOT
    provided..."). Would need a custom crewai.llms.base_llm.BaseLLM
    adapter to actually go around litellm, which wasn't attempted.

TODO once CrewAI/litellm add real support for claude-sonnet-5/claude-opus-5
tool-calling: bump the Content and Director crews back up the cost/quality
pyramid (sonnet-5 for Content's writing/QA agents, opus-5 for the
Director) — the model string is the only thing that needs to change in
each agent file, everything else (roles, goals, tools) stays as-is.
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
    return LLM(model=model, api_key=ANTHROPIC_API_KEY)
