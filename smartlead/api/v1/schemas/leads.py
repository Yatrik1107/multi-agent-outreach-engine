from pydantic import BaseModel, Field, EmailStr

class LeadInput(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    website: str = Field(default="", max_length=500)
    contact_email: str = Field(default="", max_length=320)


class ResearchResult(BaseModel):
    industry: str
    company_size: str
    recent_activity: str
    description: str


class ScoreResult(BaseModel):
    score: float = Field(..., ge=0, le=100)
    rationale: str


class OutreachDraft(BaseModel):
    subject: str
    body: str


class LeadResult(BaseModel):
    lead: LeadInput
    research: ResearchResult
    score: ScoreResult
    outreach: OutreachDraft


class LeadsProcessResponse(BaseModel):
    leads: list[LeadResult]
    errors: list[str] = Field(default_factory=list)
    
class SendOutreachEmailRequest(BaseModel):
    lead_index: int = Field(..., ge=0)
    to_email: EmailStr | None = None


class SendOutreachEmailResponse(BaseModel):
    ok: bool = True
    to: str
    message: str = "Email sent."