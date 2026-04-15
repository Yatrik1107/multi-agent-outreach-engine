from dataclasses import dataclass
import json

from smartlead.api.v1.schemas.leads import LeadInput, ResearchResult, ScoreResult
from smartlead.core.settings import Settings
from smartlead.services.llm_factory import get_llm
from smartlead.services.icp import ICP


@dataclass
class ScoringAgent:
    settings: Settings

    def score(self, lead: LeadInput, research: ResearchResult, icp: ICP) -> ScoreResult:
        if not self.settings.live_llm:
            text = f"{research.industry} {research.description} {lead.company_name}".lower()
            hits = sum(1 for kw in icp.keywords if kw.lower() in text)
            industry_hit = any(ind.lower() in text for ind in icp.target_industries)
            base = 45.0
            if industry_hit:
                base += 25.0
            base += min(20.0, hits * 5.0)
            score = round(min(100.0, base), 1)
            rationale_parts = [
                f"Keyword overlap signals: {hits} (demo heuristic).",
                f"Industry alignment (demo): {'yes' if industry_hit else 'weak'}.",
                icp.notes,
            ]
            return ScoreResult(score=score, rationale=" ".join(rationale_parts).strip())

        llm = get_llm(self.settings)
        system = (
            "You score how well a lead fits an Ideal Customer Profile (ICP). "
            "Be conservative if research quality is weak. "
            "Score must be a number from 0 to 100 with one decimal max."
        )
        user = (
            "ICP JSON:\n"
            f"{json.dumps(icp.model_dump(), indent=2)}\n\n"
            "LEAD:\n"
            f"{json.dumps(lead.model_dump(), indent=2)}\n\n"
            "RESEARCH:\n"
            f"{json.dumps(research.model_dump(), indent=2)}\n\n"
            "Return JSON with keys: score (number), rationale (string, <= 400 chars)."
        )
        return llm.generate_json(system=system, user=user, model_cls=ScoreResult, temperature=0.15)