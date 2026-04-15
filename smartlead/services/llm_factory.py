from __future__ import annotations

from smartlead.core.settings import Settings
from smartlead.services.gemini_llm import GeminiLLM
from smartlead.services.openai_llm import OpenAILLM


def get_llm(settings: Settings) -> GeminiLLM | OpenAILLM:
    p = (settings.llm_provider or "gemini").strip().lower()
    if p == "openai":
        return OpenAILLM(settings)
    if p == "gemini":
        return GeminiLLM(settings)
    raise ValueError(
        f"Unsupported LLM_PROVIDER={settings.llm_provider!r}. Use 'gemini' or 'openai'.",
    )