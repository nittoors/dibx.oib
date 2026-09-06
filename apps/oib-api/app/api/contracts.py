from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Page[T](BaseModel):
    items: list[T]
    page: int = Field(ge=1)
    size: int = Field(ge=1)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


class DepotResponse(BaseModel):
    code: str
    name: str
    location: str


class AssetResponse(BaseModel):
    asset_id: str
    depot: str
    asset_type: str
    manufacturer: str
    model: str
    age_years: float
    criticality: str
    connectivity_tier: str
    protocol: str
    health_score: float
    failure_risk_30d: float
    work_center: str
    operating_hours: int
    observed_at: datetime


class WorkforceCapacityResponse(BaseModel):
    depot: str
    occupation_code: str
    occupation: str
    assigned_workers: int
    available_workers: int
    required_workers: int
    capacity_gap: int
    training_due: int
    coverage_pct: float
    observed_at: datetime


class PartResponse(BaseModel):
    part_id: str
    fsc: str
    part_name: str
    source_count: int
    lead_time_days: int
    on_hand: int
    projected_60d_demand: int
    criticality: str
    supply_risk: float
    recommended_action: str
    scope: str
    observed_at: datetime


class ProductionFlowResponse(BaseModel):
    depot: str
    work_center: str
    weekly_plan: int
    forecast_output: int
    plan_attainment_pct: float
    queue_hours: float
    downtime_hours: float
    labor_gap_pct: float
    constraint_driver: str
    observed_at: datetime


class QualityResponse(BaseModel):
    depot: str
    work_center: str
    inspections: int
    defect_rate_pct: float
    first_pass_yield_pct: float
    open_ncr: int
    repeat_ncr: int
    top_defect: str
    ai_focus: str
    observed_at: datetime


class ConnectivityAssessmentResponse(BaseModel):
    asset_id: str
    depot: str
    asset_type: str
    manufacturer: str
    connectivity: str
    protocol: str
    data_rights: str
    cyber_status: str
    history: str
    data_quality: str
    readiness_score: int
    readiness_grade: str
    recommended_action: str
    dimension_points: dict[str, int]
    ruleset: str
    observed_at: datetime


class SubmittedAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    asset_id: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
    depot: Literal["RRAD", "ANAD", "SIAD", "WVA", "Other"]
    asset_type: str = Field(min_length=1, max_length=120)
    manufacturer: str = Field(default="", max_length=160)
    connectivity: Literal["Native Digital", "Vendor Digital", "Legacy Analog"]
    protocol: Literal[
        "MTConnect", "OPC UA", "REST API", "OEM Cloud API", "Modbus", "Serial/PLC", "None"
    ]
    data_rights: Literal["Government usable", "Limited license", "Contract unclear", "No access"]
    cyber_status: Literal["Approved", "Isolated", "Unknown", "Not assessed"]
    history: Literal[">24 months", "6-24 months", "<6 months", "None"]
    data_quality: Literal["Good", "Mixed", "Poor"]
    notes: str = Field(default="", max_length=4000)


class SubmittedAssessmentResponse(BaseModel):
    id: UUID
    asset_id: str
    depot: str
    asset_type: str
    manufacturer: str
    connectivity: str
    protocol: str
    data_rights: str
    cyber_status: str
    history: str
    data_quality: str
    notes: str
    readiness_score: int
    readiness_grade: Literal["Green", "Yellow", "Red"]
    recommended_action: str
    dimension_points: dict[str, int]
    ruleset: str
    assessed_at: datetime


class SessionResponse(BaseModel):
    subject: str
    roles: list[str]
    allowed_depots: list[str]
    authentication_mode: Literal["development", "public_readonly", "cognito"]


class AuditEventResponse(BaseModel):
    id: UUID
    occurred_at: datetime
    actor_subject: str
    action: str
    resource_type: str
    resource_id: str
    outcome: str
    depot: str | None
    request_id: str
    metadata: dict[str, object]


class ReadinessTrendResponse(BaseModel):
    reporting_period: date
    month: str
    readiness: float


class CommandKpis(BaseModel):
    composite_readiness: float
    assets_elevated: int
    workforce_gap: int
    critical_supply: int
    plan_attainment: float
    open_ncr: int
    bottlenecks: int


class AssetKpis(BaseModel):
    count: int
    average_health: float
    high_risk: int
    legacy_analog: int


class WorkforceKpis(BaseModel):
    count: int
    average_availability: float
    skill_families_at_risk: int
    training_due: int


class FlowKpis(BaseModel):
    plan_attainment: float
    bottlenecks: int
    queue_hours: float
    downtime_hours: float


class QualityKpis(BaseModel):
    inspections: int
    average_defect_rate: float
    first_pass_yield: float
    open_ncr: int


class SupplyKpis(BaseModel):
    parts: int
    critical_risks: int
    single_source: int
    average_lead_time_days: int
    scope: str


class AssessmentKpis(BaseModel):
    green: int
    yellow: int
    red: int
    ruleset: str


class ReadinessDriver(BaseModel):
    name: str
    value: float


class ReadinessSummaryResponse(BaseModel):
    depot: str
    command: CommandKpis
    assets: AssetKpis
    workforce: WorkforceKpis
    flow: FlowKpis
    quality: QualityKpis
    supply: SupplyKpis
    assessment: AssessmentKpis
    drivers: list[ReadinessDriver]
    observed_at: datetime
    source_system: str


class ImportBatchResponse(BaseModel):
    id: str
    dataset_version: str
    schema_version: str
    status: str
    manifest_sha256: str
    row_counts: dict[str, object]
    rejection_count: int
    started_at: datetime
    completed_at: datetime | None
