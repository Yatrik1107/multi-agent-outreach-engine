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
    final_outreach: OutreachDraft | None = None

    # Auto from website when CSV email empty (may be None if discovery fails).
    discovered_contact_email: str | None = None
    # User-edited To: address; wins over CSV and discovered when non-empty.
    recipient_override: str | None = None

    def effective_outreach(self) -> OutreachDraft:
        if self.final_outreach is not None:
            return self.final_outreach
        return self.outreach

    def effective_recipient(self) -> str:
        if self.recipient_override and self.recipient_override.strip():
            return self.recipient_override.strip()
        if (self.lead.contact_email or "").strip():
            return self.lead.contact_email.strip()
        if self.discovered_contact_email and self.discovered_contact_email.strip():
            return self.discovered_contact_email.strip()
        return ""


class UpdateRecipientRequest(BaseModel):
    email: str = Field(default="", max_length=320)

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


class UpdateFinalOutreachRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=300)
    body: str = Field(..., min_length=1, max_length=12000)