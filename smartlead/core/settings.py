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

    # True = no external LLM/search (demo text).
    use_mock_llm: bool = True

    # Google Gemini (AI Studio). Also accepts GOOGLE_API_KEY from the environment.
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )

    # Model id, e.g. gemini-2.0-flash, gemini-2.5-flash-preview-05-20
    gemini_model: str = "gemini-2.0-flash"

    # Optional: real web snippets for the Research agent.
    tavily_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TAVILY_API_KEY"),
    )

    @property
    def live_llm(self) -> bool:
        return (not self.use_mock_llm) and bool((self.gemini_api_key or "").strip())

    @property
    def tavily_configured(self) -> bool:
        return bool((self.tavily_api_key or "").strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()