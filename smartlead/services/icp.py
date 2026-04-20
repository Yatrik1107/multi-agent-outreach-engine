from pydantic import BaseModel, Field


DEFAULT_TEMPLATE_ID = "it"


class ICP(BaseModel):
    """Configurable Ideal Customer Profile (POC default baked in)."""

    target_industries: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    notes: str = ""


class IndustryTemplate(BaseModel):
    id: str
    label: str
    description: str = ""
    icp: ICP


def _it_default_icp() -> ICP:
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


def _healthcare_default_icp() -> ICP:
    return ICP(
        target_industries=[
            "Healthcare",
            "Digital Health",
            "HealthTech",
            "Telemedicine",
            "Medical Devices",
            "Clinical Operations",
            "Health Informatics",
            "Biotech",
        ],
        keywords=[
            "EHR",
            "HIPAA",
            "patient engagement",
            "clinical workflow",
            "care coordination",
            "telehealth",
            "remote monitoring",
            "interoperability",
            "claims automation",
            "revenue cycle",
            "compliance",
            "health analytics",
            "provider network",
        ],
        notes=(
            "Ideal customers are healthcare organizations and healthtech companies modernizing "
            "patient, provider, and operational workflows.\n\n"
            "Strong signals:\n"
            "- Mentions EHR integration, interoperability, or compliance\n"
            "- Focus on care coordination, clinical operations, or patient experience\n"
            "- Investing in automation, analytics, or remote care\n\n"
            "Moderate signals:\n"
            "- General healthcare presence but unclear software maturity\n"
            "- Pilot programs without broad rollout\n\n"
            "Weak signals:\n"
            "- Purely offline clinics with minimal digital processes\n"
            "- No evidence of IT modernization\n\n"
            "Disqualifiers:\n"
            "- No data/compliance footprint and no technology initiative\n"
            "- No operational need for scalable digital workflows"
        ),
    )


def _ecommerce_default_icp() -> ICP:
    return ICP(
        target_industries=[
            "E-commerce",
            "Retail Technology",
            "D2C",
            "Marketplace",
            "Consumer Brands",
            "Logistics Technology",
        ],
        keywords=[
            "conversion",
            "checkout",
            "cart",
            "retention",
            "LTV",
            "customer journey",
            "attribution",
            "personalization",
            "omnichannel",
            "inventory sync",
            "order management",
            "fulfillment",
            "CRM",
            "automation",
        ],
        notes=(
            "Ideal customers are growth-focused e-commerce and retail teams using digital tools "
            "to improve conversion, retention, and operational efficiency.\n\n"
            "Strong signals:\n"
            "- Active optimization of funnel, checkout, and lifecycle marketing\n"
            "- Uses modern stack integrations (CRM, analytics, fulfillment tools)\n"
            "- Scaling multi-channel acquisition and operations\n\n"
            "Moderate signals:\n"
            "- Growing online store with partial tooling\n"
            "- Basic reporting and manual workflows\n\n"
            "Weak signals:\n"
            "- Minimal online sales footprint\n"
            "- Primarily offline retail with limited e-commerce investment\n\n"
            "Disqualifiers:\n"
            "- No digital commerce model\n"
            "- No willingness to adopt integrated tooling"
        ),
    )


def _finance_default_icp() -> ICP:
    return ICP(
        target_industries=[
            "Financial Services",
            "FinTech",
            "Banking",
            "Insurance",
            "Payments",
            "Lending",
            "Wealth Management",
            "Accounting Technology",
        ],
        keywords=[
            "risk",
            "compliance",
            "KYC",
            "AML",
            "fraud detection",
            "payments",
            "transaction monitoring",
            "onboarding",
            "portfolio",
            "reconciliation",
            "reporting automation",
            "regulatory",
            "finops",
        ],
        notes=(
            "Ideal customers are finance organizations modernizing secure, compliant operations.\n\n"
            "Strong signals:\n"
            "- Mentions compliance-heavy workflows and auditability\n"
            "- Investing in automation for onboarding, risk, or reporting\n"
            "- Has integration needs across payment or core systems\n\n"
            "Moderate signals:\n"
            "- Digital products with partial process automation\n"
            "- Data systems exist but are fragmented\n\n"
            "Weak signals:\n"
            "- Mostly manual workflows and spreadsheet dependency\n"
            "- Limited appetite for systems integration\n\n"
            "Disqualifiers:\n"
            "- No digital compliance or reporting requirements\n"
            "- No operational pain tied to scale"
        ),
    )


def _manufacturing_default_icp() -> ICP:
    return ICP(
        target_industries=[
            "Manufacturing",
            "Industrial Automation",
            "Automotive",
            "Electronics Manufacturing",
            "Supply Chain",
            "Industrial IoT",
        ],
        keywords=[
            "ERP",
            "MES",
            "plant operations",
            "predictive maintenance",
            "quality control",
            "production planning",
            "inventory optimization",
            "procurement",
            "supplier management",
            "downtime",
            "SCADA",
            "lean",
            "digital twin",
        ],
        notes=(
            "Ideal customers are manufacturers improving throughput, quality, and supply chain visibility.\n\n"
            "Strong signals:\n"
            "- Modernization initiatives for plant and operations data\n"
            "- Integration requirements between ERP/MES/SCM tools\n"
            "- Clear cost pressure from downtime or planning inefficiency\n\n"
            "Moderate signals:\n"
            "- Some digitization but disconnected systems\n"
            "- Manual reporting and delayed operational insights\n\n"
            "Weak signals:\n"
            "- Paper-based or offline-first operational workflows\n"
            "- Limited process standardization\n\n"
            "Disqualifiers:\n"
            "- No measurable operations improvement goals\n"
            "- No system integration roadmap"
        ),
    )


def _education_default_icp() -> ICP:
    return ICP(
        target_industries=[
            "Education",
            "EdTech",
            "Higher Education",
            "K-12",
            "Corporate Learning",
            "Online Learning",
            "Training Platforms",
        ],
        keywords=[
            "LMS",
            "student engagement",
            "curriculum",
            "assessment",
            "retention",
            "learning analytics",
            "course management",
            "admissions",
            "academic operations",
            "credentialing",
            "cohort",
            "skills tracking",
        ],
        notes=(
            "Ideal customers are education organizations improving learner outcomes and administrative efficiency.\n\n"
            "Strong signals:\n"
            "- Prioritizes learner engagement, retention, and measurable outcomes\n"
            "- Uses LMS and learning data in day-to-day workflows\n"
            "- Needs automation for operations like enrollment or reporting\n\n"
            "Moderate signals:\n"
            "- Digital coursework exists but adoption is inconsistent\n"
            "- Manual coordination across departments\n\n"
            "Weak signals:\n"
            "- Limited digital infrastructure for teaching operations\n"
            "- No evidence of data-driven learning initiatives\n\n"
            "Disqualifiers:\n"
            "- No digital delivery or scaling goals\n"
            "- Budget or process constraints with no modernization path"
        ),
    )


def _real_estate_default_icp() -> ICP:
    return ICP(
        target_industries=[
            "Real Estate",
            "Property Technology",
            "Commercial Real Estate",
            "Property Management",
            "Brokerage",
            "Construction Technology",
        ],
        keywords=[
            "property management",
            "tenant experience",
            "leasing",
            "portfolio operations",
            "facility management",
            "maintenance automation",
            "CRM",
            "listing workflow",
            "asset management",
            "occupancy",
            "workflow automation",
            "document management",
        ],
        notes=(
            "Ideal customers are real estate operators digitizing leasing, tenant, and portfolio workflows.\n\n"
            "Strong signals:\n"
            "- Multi-property operations with scaling pain\n"
            "- Clear need for CRM/workflow/document integration\n"
            "- Focus on occupancy, leasing speed, or tenant retention\n\n"
            "Moderate signals:\n"
            "- Digital tools in place but manual handoffs remain\n"
            "- Reporting exists with limited real-time visibility\n\n"
            "Weak signals:\n"
            "- Small local operations with minimal software usage\n"
            "- No formal process for pipeline or tenant lifecycle\n\n"
            "Disqualifiers:\n"
            "- No recurring portfolio/tenant operations to optimize\n"
            "- No intent to improve digital process maturity"
        ),
    )


def _logistics_default_icp() -> ICP:
    return ICP(
        target_industries=[
            "Logistics",
            "Transportation",
            "Freight",
            "Supply Chain Technology",
            "Warehousing",
            "Last-mile Delivery",
        ],
        keywords=[
            "fleet",
            "dispatch",
            "route optimization",
            "shipment tracking",
            "WMS",
            "TMS",
            "carrier management",
            "fulfillment",
            "inventory visibility",
            "ETA",
            "proof of delivery",
            "operations automation",
        ],
        notes=(
            "Ideal customers are logistics operators improving delivery performance and operational control.\n\n"
            "Strong signals:\n"
            "- Active optimization of routes, dispatch, or warehouse workflows\n"
            "- Requires integrations across shipping, inventory, and reporting systems\n"
            "- Has KPI pressure around on-time delivery and cost-to-serve\n\n"
            "Moderate signals:\n"
            "- Partial digital tooling with operational bottlenecks\n"
            "- Data available but not unified for decision making\n\n"
            "Weak signals:\n"
            "- Mostly manual planning and low shipment complexity\n"
            "- No measurable operations transformation goals\n\n"
            "Disqualifiers:\n"
            "- Low process complexity with no scaling pressure\n"
            "- No software adoption roadmap"
        ),
    )


def _professional_services_default_icp() -> ICP:
    return ICP(
        target_industries=[
            "Professional Services",
            "Consulting",
            "Legal Services",
            "Accounting Services",
            "Marketing Agencies",
            "Recruitment",
        ],
        keywords=[
            "client delivery",
            "project management",
            "time tracking",
            "resource planning",
            "proposal workflow",
            "CRM",
            "billing automation",
            "knowledge management",
            "document workflow",
            "SLA",
            "pipeline visibility",
            "capacity planning",
        ],
        notes=(
            "Ideal customers are service firms scaling delivery quality and utilization through better systems.\n\n"
            "Strong signals:\n"
            "- Multi-client delivery with repeatable workflows\n"
            "- Need to connect CRM, project, and billing tools\n"
            "- Emphasis on utilization, margins, and operational consistency\n\n"
            "Moderate signals:\n"
            "- Team uses digital tools but with manual coordination\n"
            "- Reporting is periodic and reactive\n\n"
            "Weak signals:\n"
            "- Very small practices with low process complexity\n"
            "- No evidence of digital process ownership\n\n"
            "Disqualifiers:\n"
            "- No repeatable workflow to optimize\n"
            "- No need for cross-tool automation"
        ),
    )


def _fmcg_default_icp() -> ICP:
    return ICP(
        target_industries=[
            "FMCG",
            "Consumer Goods",
            "CPG",
            "Food & Beverage",
            "Personal Care",
            "Household Products",
            "Retail Distribution",
        ],
        keywords=[
            "sell-through",
            "distribution",
            "retail execution",
            "trade promotion",
            "SKU",
            "category management",
            "demand forecasting",
            "inventory turnover",
            "merchandising",
            "supply planning",
            "channel performance",
            "field sales",
            "route-to-market",
        ],
        notes=(
            "Ideal customers are FMCG and consumer goods companies optimizing high-volume product "
            "operations across channels, distributors, and retail partners.\n\n"
            "Strong signals:\n"
            "- Multi-brand or multi-channel distribution complexity\n"
            "- Active focus on demand planning, inventory, and promotion effectiveness\n"
            "- Needs integration between sales, supply chain, and analytics systems\n\n"
            "Moderate signals:\n"
            "- Established retail footprint with partially digitized operations\n"
            "- Reporting exists but lacks real-time visibility\n\n"
            "Weak signals:\n"
            "- Single-location or low-volume operations with limited process depth\n"
            "- Minimal data-driven planning and manual coordination\n\n"
            "Disqualifiers:\n"
            "- No recurring distribution or channel management workflows\n"
            "- No intent to improve operational scalability"
        ),
    )


def get_industry_templates() -> list[IndustryTemplate]:
    return [
        IndustryTemplate(
            id="it",
            label="IT",
            description="Software, SaaS, and broader technology companies.",
            icp=_it_default_icp(),
        ),
        IndustryTemplate(
            id="healthcare",
            label="Healthcare",
            description="Healthcare providers and healthtech organizations.",
            icp=_healthcare_default_icp(),
        ),
        IndustryTemplate(
            id="ecommerce",
            label="E-commerce",
            description="Digital commerce, D2C, and retail technology teams.",
            icp=_ecommerce_default_icp(),
        ),
        IndustryTemplate(
            id="finance",
            label="Finance",
            description="Banking, fintech, insurance, and payments organizations.",
            icp=_finance_default_icp(),
        ),
        IndustryTemplate(
            id="manufacturing",
            label="Manufacturing",
            description="Industrial, operations, and supply chain organizations.",
            icp=_manufacturing_default_icp(),
        ),
        IndustryTemplate(
            id="education",
            label="Education",
            description="Schools, edtech, and training organizations.",
            icp=_education_default_icp(),
        ),
        IndustryTemplate(
            id="real_estate",
            label="Real Estate",
            description="Property, brokerage, and portfolio operations teams.",
            icp=_real_estate_default_icp(),
        ),
        IndustryTemplate(
            id="logistics",
            label="Logistics",
            description="Freight, delivery, transportation, and warehousing teams.",
            icp=_logistics_default_icp(),
        ),
        IndustryTemplate(
            id="professional_services",
            label="Professional Services",
            description="Consulting, agencies, and service-led firms.",
            icp=_professional_services_default_icp(),
        ),
        IndustryTemplate(
            id="fmcg",
            label="FMCG",
            description="Consumer goods and high-volume retail distribution organizations.",
            icp=_fmcg_default_icp(),
        ),
    ]


def get_template_by_id(template_id: str) -> IndustryTemplate | None:
    target = (template_id or "").strip().lower()
    for template in get_industry_templates():
        if template.id == target:
            return template
    return None


def get_default_template_id() -> str:
    return DEFAULT_TEMPLATE_ID


def get_default_icp() -> ICP:
    template = get_template_by_id(get_default_template_id())
    if template is None:
        return ICP()
    return template.icp.model_copy(deep=True)