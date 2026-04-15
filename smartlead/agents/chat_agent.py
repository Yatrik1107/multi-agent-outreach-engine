from dataclasses import dataclass

from smartlead.core.settings import Settings
from smartlead.services.llm_factory import get_llm


@dataclass
class ChatAgent:
    settings: Settings

    def reply(
        self,
        user_text: str,
        history: list[dict[str, str]],
        *,
        pipeline_context: str | None = None,
    ) -> str:
        if not self.settings.live_llm:
            base = (
                "Thanks for your message (demo mode). I'm the Smart Lead Assistant. "
                "Configure ICP under the ICP tab, upload leads, then ask about scores. "
                "Set USE_MOCK_LLM=false and an API key for live LLM."
            )
            if pipeline_context:
                return (
                    f"{base}\n\n---\nLast lead run (server memory; demo text only):\n"
                    f"{pipeline_context[:8000]}"
                )
            return base

        llm = get_llm(self.settings)
        system = (
            "You are the Smart Lead Qualifier assistant for a B2B sales POC. "
            "Be concise, professional, and helpful.\n"
            "Rules:\n"
            "1) If the user message block contains PIPELINE_SUMMARY with lead_count >= 1, "
            "you already have processed leads on the server. Answer using companies_in_order "
            "and scores. Never tell the user to run the pipeline for questions about that data.\n"
            "2) If there is no pipeline run (no PIPELINE_SUMMARY or lead_count 0) and the user "
            "asks about their scored leads, say they should run the pipeline on the Leads tab.\n"
            "3) When CURRENT_ICP appears, use it to explain fit vs scoring rationale.\n"
            "No harmful content."
        )
        transcript_lines: list[str] = []
        for m in history[-24:]:
            role = m.get("role", "user")
            content = (m.get("content") or "").strip()
            if not content:
                continue
            transcript_lines.append(f"{role.upper()}: {content}")
        transcript = "\n".join(transcript_lines).strip()

        ctx_block = ""
        if pipeline_context:
            ctx_block = (
                "CONTEXT (pipeline + ICP; authoritative for lead lists and scores):\n"
                f"{pipeline_context}\n\n---\n\n"
            )

        user_block = (
            f"{ctx_block}"
            f"Conversation so far:\n{transcript}\n\n"
            f"Latest user request: {user_text}\n\n"
            "Reply as ASSISTANT (plain text, no role labels)."
        )
        temp = 0.35 if pipeline_context else 0.7
        return llm.generate_text(system=system, user=user_block, temperature=temp)