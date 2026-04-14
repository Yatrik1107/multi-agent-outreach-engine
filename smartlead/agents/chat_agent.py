from dataclasses import dataclass

from smartlead.core.settings import Settings
from smartlead.services.gemini_llm import GeminiLLM


@dataclass
class ChatAgent:
    settings: Settings

    def reply(self, user_text: str, history: list[dict[str, str]]) -> str:
        if not self.settings.live_llm:
            return (
                "Thanks for your message (demo mode). I'm the Smart Lead Assistant. "
                "Set USE_MOCK_LLM=false and GEMINI_API_KEY to use Gemini, or keep mock mode."
            )

        llm = GeminiLLM(self.settings)
        system = (
            "You are the Smart Lead Qualifier assistant for a B2B sales POC. "
            "Be concise, professional, and helpful. You can explain: CSV upload for leads, "
            "research/scoring/outreach pipeline, and ICP concepts. No harmful content."
        )
        transcript_lines: list[str] = []
        for m in history[-24:]:
            role = m.get("role", "user")
            content = (m.get("content") or "").strip()
            if not content:
                continue
            transcript_lines.append(f"{role.upper()}: {content}")
        transcript = "\n".join(transcript_lines).strip()
        user_block = (
            f"Conversation so far:\n{transcript}\n\n"
            f"USER: {user_text}\n\n"
            "Reply as ASSISTANT (plain text, no role labels)."
        )
        return llm.generate_text(system=system, user=user_block, temperature=0.7)