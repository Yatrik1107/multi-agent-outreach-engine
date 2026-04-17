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
        contact_hint_email: str | None = None,
    ) -> OutreachDraft:
        sig = self.settings.outreach_signature_block()
        sig_instruction = (
            "End the email body with this exact sign-off block (plain text, final lines):\n"
            f"{sig}\n"
            if sig
            else (
                "End with a short professional sign-off. If no sender profile is configured, "
                "you may use the placeholders: Your Name, Your Position, Your Company Name."
            )
        )

        if not self.settings.live_llm:
            subject = f"Idea for {lead.company_name} ({research.industry.split('/')[0].strip()})"
            raw = (contact_hint_email or lead.contact_email or "").strip()
            who = raw if raw else "there"
            closing = sig if sig else "Best,\nSmart Lead POC"
            body = (
                f"Hi {who},\n\n"
                f"I’ve been looking at {lead.company_name} and noticed {research.recent_activity.lower()}\n"
                f"Score vs our ICP (internal demo): {score.score}/100.\n\n"
                f"Context (demo research): {research.description}\n\n"
                f"Would you be open to a quick chat next week?\n\n"
                f"{closing}"
            )
            return OutreachDraft(subject=subject, body=body)

        llm = get_llm(self.settings)
        system = (
            "You write a short, personalized B2B outreach email. "
            "Be professional, specific, and non-spammy. No fabricated metrics or claims not supported "
            "by the research text. Subject <= 90 chars. Body <= 1800 chars, plain text.\n"
            f"{sig_instruction}"
        )
        user = (
            "LEAD:\n"
            f"{json.dumps(lead.model_dump(), indent=2)}\n\n"
            "RESEARCH:\n"
            f"{json.dumps(research.model_dump(), indent=2)}\n\n"
            "SCORE:\n"
            f"{json.dumps(score.model_dump(), indent=2)}\n\n"
            "Return JSON with keys: subject (string), body (string). "
            "The body must include the requested sign-off as the last lines."
            f"CONTACT_HINT_EMAIL (optional; use for greeting only if appropriate): "
            f"{contact_hint_email or '(none)'}\n\n"
        )
        draft = llm.generate_json(system=system, user=user, model_cls=OutreachDraft, temperature=0.65)
        draft.body = self._apply_signature_fallback(draft.body)
        return draft
    
    def _apply_signature_fallback(self, body: str) -> str:
        sig = self.settings.outreach_signature_block()
        if not sig:
            return body

        normalized = (body or "").strip()

        # Replace placeholder tokens when present.
        normalized = normalized.replace("[Your Name]", self.settings.outreach_sender_name or "Your Name")
        normalized = normalized.replace("[Your Position]", self.settings.outreach_sender_role or "Your Position")
        normalized = normalized.replace("[Your Company Name]", self.settings.outreach_sender_company or "Your Company Name")
        normalized = normalized.replace("Your Name", self.settings.outreach_sender_name or "Your Name")
        normalized = normalized.replace("Your Position", self.settings.outreach_sender_role or "Your Position")
        normalized = normalized.replace("Your Company Name", self.settings.outreach_sender_company or "Your Company Name")

        sig_clean = sig.strip()
        text = normalized.rstrip()

        # If exact signature already at the end, keep it as-is (no duplication).
        if text.endswith(sig_clean):
            return text

        # Remove duplicate trailing signature blocks if model generated them multiple times.
        double_sig = (sig_clean + "\n\n" + sig_clean)
        while text.endswith(double_sig):
            text = text[: -len(sig_clean)].rstrip()

        # Remove generic trailing sign-off-only line if present.
        lines = text.splitlines()
        while lines and lines[-1].strip().lower() in {"best", "best regards,", "regards,", "thanks,", "thank you,"}:
            lines.pop()

        text = "\n".join(lines).rstrip()
        return text + "\n\n" + sig_clean