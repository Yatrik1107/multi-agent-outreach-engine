from pydantic import BaseModel, Field

from smartlead.services.icp import ICP


class ApplyTemplateRequest(BaseModel):
    template_id: str = Field(..., min_length=1, max_length=100)


class ICPStateResponse(BaseModel):
    active_template_id: str
    target_industries: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    notes: str = ""


class IndustryTemplateResponse(BaseModel):
    id: str
    label: str
    description: str = ""
    icp: ICP
