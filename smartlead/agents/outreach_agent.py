from dataclasses import dataclass
import json

from smartlead.api.v1.schemas.leads import (
    LeadInput,
    OutreachDraft,
    ResearchResult,
    ScoreResult,
)
from smartlead.core.settings import Settings
from smartlead.services.llm_factory import get_llm


@dataclass
class OutreachAgent:
    settings: Settings

    def draft(
        self,
        lead: LeadInput,
        research: ResearchResult,
        score: ScoreResult,
    ) -> OutreachDraft:
        if not self.settings.live_llm:
            subject = f"Idea for {lead.company_name} ({research.industry.split('/')[0].strip()})"
            who = lead.contact_email or "there"
            body = (
                f"Hi {who},\n\n"
                f"I’ve been looking at {lead.company_name} and noticed {research.recent_activity.lower()}\n"
                f"Score vs our ICP (internal demo): {score.score}/100.\n\n"
                f"Context (demo research): {research.description}\n\n"
                f"Would you be open to a quick chat next week?\n\n"
                f"Best,\nSmart Lead POC"
            )
            return OutreachDraft(subject=subject, body=body)

        llm = get_llm(self.settings)
        system = (
            "You write a short, personalized B2B outreach email. "
            "Be professional, specific, and non-spammy. No fabricated metrics or claims not supported "
            "by the research text. Subject <= 90 chars. Body <= 1800 chars, plain text."
        )
        user = (
            "LEAD:\n"
            f"{json.dumps(lead.model_dump(), indent=2)}\n\n"
            "RESEARCH:\n"
            f"{json.dumps(research.model_dump(), indent=2)}\n\n"
            "SCORE:\n"
            f"{json.dumps(score.model_dump(), indent=2)}\n\n"
            "Return JSON with keys: subject (string), body (string)."
        )
        return llm.generate_json(system=system, user=user, model_cls=OutreachDraft, temperature=0.65)