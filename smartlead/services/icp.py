from pydantic import BaseModel, Field


class ICP(BaseModel):
    """Configurable Ideal Customer Profile (POC default baked in)."""

    target_industries: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    notes: str = ""


def get_default_icp() -> ICP:
    return ICP(
        target_industries=["Software", "Information Technology", "SaaS"],
        keywords=["cloud", "automation", "API", "B2B"],
        notes="Mid-market B2B teams adopting automation (POC default ICP).",
    )