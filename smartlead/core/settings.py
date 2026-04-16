from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Smart Lead Qualifier & Outreach"
    debug: bool = False

    cors_origins: str = "*"

    # True = no external LLM (demo text).
    use_mock_llm: bool = True

    # "gemini" | "openai" | "grok" (case-insensitive). Controls which API key is required when USE_MOCK_LLM=false.
    llm_provider: str = "gemini"

    # --- Google Gemini ---
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    gemini_model: str = "gemini-2.0-flash"

    # --- OpenAI ---
    # Accepts OPENAI_API_KEY or OPENAPI_API_KEY (common typo).
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "OPENAPI_API_KEY"),
    )
    openai_model: str = "gpt-4o-mini"
    
    # --- xAI Grok (optional LLM; OpenAI-compatible base URL) ---
    grok_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GROK_API_KEY", "XAI_API_KEY"),
    )
    grok_model: str = "grok-4-1-fast-non-reasoning"

    tavily_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TAVILY_API_KEY"),
    )
    
    # Sign-off for outreach emails (optional).
    outreach_sender_name: str = ""
    outreach_sender_role: str = ""
    outreach_sender_company: str = ""
    
     # --- Gmail SMTP ---
    sender_email: str = ""
    gmail_smtp_key: str = Field(
        default="",
        validation_alias=AliasChoices("GMAIL_SMTP_KEY", "GMAIL_APP_PASSWORD"),
    )
    
    # When True and CSV has no contact email, try to find an address on the company website (homepage HTML).
    enable_contact_email_discovery: bool = True
    contact_discovery_max_bytes: int = 500_000

    def _provider_normalized(self) -> str:
        return (self.llm_provider or "gemini").strip().lower()

    @property
    def has_active_llm_credentials(self) -> bool:
        p = self._provider_normalized()
        if p == "openai":
            return bool((self.openai_api_key or "").strip())
        if p == "gemini":
            return bool((self.gemini_api_key or "").strip())
        if p == "grok":
            return bool((self.grok_api_key or "").strip())
        return False

    @property
    def live_llm(self) -> bool:
        return (not self.use_mock_llm) and self.has_active_llm_credentials

    @property
    def tavily_configured(self) -> bool:
        return bool((self.tavily_api_key or "").strip())
    
    def outreach_signature_block(self) -> str | None:
        name = (self.outreach_sender_name or "").strip()
        role = (self.outreach_sender_role or "").strip()
        company = (self.outreach_sender_company or "").strip()
        if not name and not role and not company:
            return None
        lines = ["Best regards,"]
        if name:
            lines.append(name)
        if role:
            lines.append(role)
        if company:
            lines.append(company)
        return "\n".join(lines)

    def live_llm_config_error_detail(self) -> str:
        p = self._provider_normalized()
        if p == "openai":
            return (
                "LLM_PROVIDER=openai requires OPENAI_API_KEY or OPENAPI_API_KEY. "
                "Or set USE_MOCK_LLM=true."
            )
        if p == "gemini":
            return (
                "LLM_PROVIDER=gemini requires GEMINI_API_KEY or GOOGLE_API_KEY. "
                "Or set USE_MOCK_LLM=true."
            )
        if p == "grok":
            return (
                "LLM_PROVIDER=grok requires GROK_API_KEY (or XAI_API_KEY). "
                "Or set USE_MOCK_LLM=true."
            )
        return (
            f"Unknown LLM_PROVIDER={self.llm_provider!r}. Use 'gemini', 'openai', or 'grok'. "
            "Or set USE_MOCK_LLM=true."
        )
        
    @property
    def gmail_outreach_configured(self) -> bool:
        return bool(
            (self.sender_email or "").strip() and (self.gmail_smtp_key or "").strip(),
        )

@lru_cache
def get_settings() -> Settings:
    return Settings()