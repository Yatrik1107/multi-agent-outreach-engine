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
                "Upload a CSV on the Leads tab, then ask about scores or drafts. "
                "Set USE_MOCK_LLM=false and GEMINI_API_KEY for live Gemini."
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
            "Be concise, professional, and helpful. You can explain: CSV upload for leads, "
            "research/scoring/outreach pipeline, and ICP concepts. "
            "When CONTEXT from the last pipeline run is provided below, use it to answer "
            "questions about specific companies, scores, email drafts, and research fields. "
            "If the user asks about leads but no CONTEXT is present, say they should run "
            "the pipeline on the Leads tab first. No harmful content."
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
                "CONTEXT (last successful lead pipeline run on this server):\n"
                f"{pipeline_context}\n\n---\n\n"
            )

        user_block = (
            f"{ctx_block}"
            f"Conversation so far:\n{transcript}\n\n"
            f"USER: {user_text}\n\n"
            "Reply as ASSISTANT (plain text, no role labels)."
        )
        return llm.generate_text(system=system, user=user_block, temperature=0.7)