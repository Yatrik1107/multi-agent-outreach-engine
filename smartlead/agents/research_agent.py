from dataclasses import dataclass

from smartlead.api.v1.schemas.leads import LeadInput, ResearchResult
from smartlead.core.settings import Settings
from smartlead.services.gemini_llm import GeminiLLM
from smartlead.services.tavily_search import fetch_search_context


@dataclass
class ResearchAgent:
    settings: Settings

    def research(self, lead: LeadInput) -> ResearchResult:
        if not self.settings.live_llm:
            site = lead.website or "unknown"
            return ResearchResult(
                industry="Software / Technology (demo)",
                company_size="51–200 employees (demo)",
                recent_activity="Recently mentioned digital transformation initiatives (demo).",
                description=(
                    f"{lead.company_name} appears to operate a B2B-focused model based on "
                    f"public signals (demo). Website/context: {site}."
                ),
            )

        llm = GeminiLLM(self.settings)
        query = f"{lead.company_name} company official website industry employees news"
        web_block = fetch_search_context(self.settings, query)
        if web_block:
            evidence = (
                "WEB_SEARCH_SNIPPETS (from Tavily; may be incomplete or wrong; cite uncertainty):\n"
                f"{web_block}\n"
            )
        else:
            evidence = (
                "NO_LIVE_WEB_SEARCH: infer cautiously from company name and website string only; "
                "state uncertainty explicitly in the description.\n"
            )

        user = (
            f"Company name: {lead.company_name}\n"
            f"Website or domain hint: {lead.website or '(none)'}\n"
            f"Contact email (optional): {lead.contact_email or '(none)'}\n\n"
            f"{evidence}\n"
            "Return JSON fields: industry, company_size, recent_activity, description.\n"
            "- industry: short label\n"
            "- company_size: estimated size bucket or 'Unknown'\n"
            "- recent_activity: one sentence on recent public signal if any, else 'Unknown'\n"
            "- description: 2–4 sentences; if evidence is weak, say so explicitly.\n"
        )
        system = "You extract factual-style company research fields for sales qualification."
        return llm.generate_json(system=system, user=user, model_cls=ResearchResult, temperature=0.2)