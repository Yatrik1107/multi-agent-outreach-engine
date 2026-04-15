from pydantic import BaseModel, Field


class ICP(BaseModel):
    """Configurable Ideal Customer Profile (POC default baked in)."""

    target_industries: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    notes: str = ""


def get_default_icp() -> ICP:
    return ICP(
        target_industries=[
            "Software",
            "SaaS",
            "Information Technology",
            "FinTech",
            "HealthTech",
            "E-commerce",
            "Marketing Technology",
            "AI/ML",
            "Cybersecurity",
            "Cloud Services",
        ],
        keywords=[
            "cloud",
            "SaaS",
            "API",
            "automation",
            "workflow",
            "integration",
            "B2B",
            "platform",
            "dashboard",
            "analytics",
            "CRM",
            "AI",
            "machine learning",
            "DevOps",
            "no-code",
            "low-code",
            "data pipeline",
            "microservices",
            "enterprise software",
            "productivity",
        ],
        notes=(
            "Ideal customers are mid-market to enterprise B2B companies that rely on software "
            "to scale operations. They typically have digital products, engineering teams, or "
            "data-driven workflows.\n\n"
            "Strong signals:\n"
            "- Uses APIs, integrations, or cloud infrastructure\n"
            "- Offers SaaS or platform-based solutions\n"
            "- Mentions automation, analytics, or scalability\n"
            "- Has active product or engineering hiring\n\n"
            "Moderate signals:\n"
            "- Digital presence but unclear tech stack\n"
            "- Uses basic tools but may upgrade\n\n"
            "Weak signals:\n"
            "- Service-only businesses with no software component\n"
            "- Offline-first or low-tech businesses\n\n"
            "Disqualifiers:\n"
            "- Small local businesses with no tech adoption\n"
            "- Industries with low digital transformation\n\n"
            "Goal: prioritize leads likely to benefit from automation, integrations, or scalable software solutions."
        ),
    )