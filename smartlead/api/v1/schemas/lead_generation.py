from pydantic import BaseModel, Field


class LeadGenerationRequest(BaseModel):
    geo: str = Field(..., min_length=1, max_length=300)
    sector: str = Field(..., min_length=1, max_length=1200)
    keywords: str = Field(default="", max_length=1200)
    max_results: int = Field(default=20, ge=1, le=100)
    enable_email_discovery: bool | None = None


class GeneratedLead(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    website: str = Field(default="", max_length=500)
    contact_email: str = Field(default="", max_length=320)
    confidence: float = Field(default=0.0, ge=0, le=1)
    source_query: str = Field(default="", max_length=500)
    source_url: str = Field(default="", max_length=500)


class LeadGenerationResponse(BaseModel):
    leads: list[GeneratedLead]
    warnings: list[str] = Field(default_factory=list)
    generated_count: int


class GeneratedLeadsStateResponse(BaseModel):
    available: bool
    lead_count: int
    warnings: list[str] = Field(default_factory=list)
