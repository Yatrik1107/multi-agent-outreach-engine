from collections.abc import Iterator
from typing import Any

from smartlead.agents.outreach_agent import OutreachAgent
from smartlead.agents.research_agent import ResearchAgent
from smartlead.agents.scoring_agent import ScoringAgent
from smartlead.api.v1.schemas.leads import LeadInput, LeadResult
from smartlead.core.settings import Settings
from smartlead.services.icp import ICP
from smartlead.services.email_discovery import discover_email_from_website


def _discovered_email(lead: LeadInput, settings: Settings) -> str | None:
    if not getattr(settings, "enable_contact_email_discovery", True):
        return None
    if (lead.contact_email or "").strip():
        return None
    if not (lead.website or "").strip():
        return None
    max_b = int(getattr(settings, "contact_discovery_max_bytes", 500_000) or 500_000)
    return discover_email_from_website(lead.website, max_bytes=max_b)

def run_pipeline(leads: list[LeadInput], icp: ICP, settings: Settings) -> list[LeadResult]:
    research_agent = ResearchAgent(settings=settings)
    scoring_agent = ScoringAgent(settings=settings)
    outreach_agent = OutreachAgent(settings=settings)

    results: list[LeadResult] = []
    for lead in leads:
        discovered = _discovered_email(lead, settings)
        research = research_agent.research(lead)
        score = scoring_agent.score(lead, research, icp)
        outreach = outreach_agent.draft(lead, research, score, contact_hint_email=discovered or lead.contact_email or None)
        results.append(
            LeadResult(
                lead=lead,
                research=research,
                score=score,
                outreach=outreach,
                final_outreach=None,
                discovered_contact_email=discovered,
                recipient_override=None,
            ),
        )
    return results


def iter_pipeline_events(
    leads: list[LeadInput],
    icp: ICP,
    settings: Settings,
    parse_errors: list[str],
) -> Iterator[dict[str, Any]]:
    research_agent = ResearchAgent(settings=settings)
    scoring_agent = ScoringAgent(settings=settings)
    outreach_agent = OutreachAgent(settings=settings)

    n = len(leads)
    results: list[LeadResult] = []

    yield {
        "event": "start",
        "total": n,
        "parse_warnings": parse_errors,
    }

    for idx, lead in enumerate(leads, start=1):
        company = lead.company_name

        yield {
            "event": "step",
            "phase": "research",
            "index": idx,
            "total": n,
            "company": company,
            "message": f"Researching {company} ({idx}/{n})…",
        }
        discovered = _discovered_email(lead, settings)
        research = research_agent.research(lead)

        yield {
            "event": "step",
            "phase": "scoring",
            "index": idx,
            "total": n,
            "company": company,
            "message": f"Scoring {company} ({idx}/{n})…",
        }
        score = scoring_agent.score(lead, research, icp)

        yield {
            "event": "step",
            "phase": "outreach",
            "index": idx,
            "total": n,
            "company": company,
            "message": f"Drafting outreach for {company} ({idx}/{n})…",
        }
        outreach = outreach_agent.draft(lead, research, score, contact_hint_email=discovered or lead.contact_email or None)

        result = LeadResult(
                lead=lead,
                research=research,
                score=score,
                outreach=outreach,
                final_outreach=None,
                discovered_contact_email=discovered,
                recipient_override=None,
            )
        results.append(result)
        yield {"event": "lead", "data": result.model_dump()}

    yield {
        "event": "complete",
        "errors": parse_errors,
        "lead_count": len(results),
    }
    
def run_single_lead(lead: LeadInput, icp: ICP, settings: Settings) -> LeadResult:
    """Re-run research → score → outreach for one lead (clears any prior final_outreach)."""
    discovered = _discovered_email(lead, settings)
    research_agent = ResearchAgent(settings=settings)
    scoring_agent = ScoringAgent(settings=settings)
    outreach_agent = OutreachAgent(settings=settings)

    research = research_agent.research(lead)
    score = scoring_agent.score(lead, research, icp)
    outreach = outreach_agent.draft(lead, research, score, contact_hint_email=discovered or lead.contact_email or None)
    return LeadResult(
        lead=lead,
        research=research,
        score=score,
        outreach=outreach,
        final_outreach=None,
        discovered_contact_email=discovered,
        recipient_override=None,
    )