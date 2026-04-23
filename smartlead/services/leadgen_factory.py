from __future__ import annotations

from smartlead.core.settings import Settings
from smartlead.services.lead_generation import ExaLeadGeneratorService
from smartlead.services.google_lead_generation import GoogleLeadGeneratorService
from smartlead.services.openai_lead_generation import OpenAILeadGeneratorService
from smartlead.services.tavily_lead_generation import TavilyLeadGeneratorService


def get_lead_generator(
    settings: Settings,
) -> GoogleLeadGeneratorService | OpenAILeadGeneratorService | ExaLeadGeneratorService | TavilyLeadGeneratorService:
    p = (settings.leadgen_provider or "google").strip().lower()
    if p == "google":
        return GoogleLeadGeneratorService(settings)
    if p == "openai":
        return OpenAILeadGeneratorService(settings)
    if p == "exa":
        return ExaLeadGeneratorService(settings)
    if p == "tavily":
        return TavilyLeadGeneratorService(settings)
    raise ValueError(
        f"Unsupported LEADGEN_PROVIDER={settings.leadgen_provider!r}. "
        "Use 'google', 'openai', 'exa', or 'tavily'.",
    )