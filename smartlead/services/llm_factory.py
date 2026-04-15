from __future__ import annotations

from smartlead.core.settings import Settings
from smartlead.services.gemini_llm import GeminiLLM
from smartlead.services.grok_llm import GrokLLM
from smartlead.services.openai_llm import OpenAILLM


def get_llm(settings: Settings) -> GeminiLLM | OpenAILLM | GrokLLM:
    p = (settings.llm_provider or "gemini").strip().lower()
    if p == "openai":
        return OpenAILLM(settings)
    if p == "gemini":
        return GeminiLLM(settings)
    if p == "grok":
        return GrokLLM(settings)
    raise ValueError(
        f"Unsupported LLM_PROVIDER={settings.llm_provider!r}. "
        "Use 'gemini', 'openai', or 'grok'.",
    )