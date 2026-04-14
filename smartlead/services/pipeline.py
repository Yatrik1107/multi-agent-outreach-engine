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