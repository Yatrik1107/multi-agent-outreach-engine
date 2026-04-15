from collections.abc import Iterator
from typing import Any

from smartlead.agents.outreach_agent import OutreachAgent
from smartlead.agents.research_agent import ResearchAgent
from smartlead.agents.scoring_agent import ScoringAgent
from smartlead.api.v1.schemas.leads import LeadInput, LeadResult
from smartlead.core.settings import Settings
from smartlead.services.icp import ICP


def run_pipeline(leads: list[LeadInput], icp: ICP, settings: Settings) -> list[LeadResult]:
    research_agent = ResearchAgent(settings=settings)
    scoring_agent = ScoringAgent(settings=settings)
    outreach_agent = OutreachAgent(settings=settings)

    results: list[LeadResult] = []
    for lead in leads:
        research = research_agent.research(lead)
        score = scoring_agent.score(lead, research, icp)
        outreach = outreach_agent.draft(lead, research, score)
        results.append(
            LeadResult(
                lead=lead,
                research=research,
                score=score,
                outreach=outreach,
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
        outreach = outreach_agent.draft(lead, research, score)

        result = LeadResult(
            lead=lead,
            research=research,
            score=score,
            outreach=outreach,
        )
        results.append(result)
        yield {"event": "lead", "data": result.model_dump()}

    yield {
        "event": "complete",
        "errors": parse_errors,
        "lead_count": len(results),
    }