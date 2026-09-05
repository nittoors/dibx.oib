from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictRow(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ManifestFile(BaseModel):
    dataset: str
    path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    row_count: int = Field(ge=0)


class SeedManifest(BaseModel):
    dataset_version: str
    schema_version: str
    source_code: str
    source_name: str
    source_classification: Literal["SYNTHETIC"]
    source_description: str
    observed_at: datetime
    reporting_year: int = Field(ge=2000, le=2100)
    files: list[ManifestFile]


class AssetRow(StrictRow):
    asset_id: str
    depot: str
    asset_type: str
    manufacturer: str
    model: str
    age_years: Decimal = Field(ge=0)
    criticality: Literal["Low", "Medium", "High"]
    connectivity_tier: str
    protocol: str
    health_score: Decimal = Field(ge=0, le=100)
    failure_risk_30d: Decimal = Field(ge=0, le=100)
    work_center: str
    operating_hours: int = Field(ge=0)


class ConnectivityRow(StrictRow):
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
    readiness_score: int = Field(ge=0, le=100)
    readiness_grade: Literal["Green", "Yellow", "Red"]
    recommended_action: str


class DepotReadinessRow(StrictRow):
    depot: str
    name: str
    location: str
    readiness: Decimal = Field(ge=0, le=100)
    asset_risk: Decimal = Field(ge=0, le=100)
    workforce_gap: Decimal = Field(ge=0)
    supply_risk: Decimal = Field(ge=0, le=100)
    plan_attainment: Decimal = Field(ge=0)
    open_quality: int = Field(ge=0)
    top_drivers: str


class PartRow(StrictRow):
    part_id: str
    fsc: str
    part_name: str
    source_count: int = Field(ge=0)
    lead_time_days: int = Field(ge=0)
    on_hand: int = Field(ge=0)
    projected_60d_demand: int = Field(ge=0)
    criticality: Literal["Low", "Medium", "High", "Critical"]
    supply_risk: Decimal = Field(ge=0, le=100)
    recommended_action: str


class ProductionFlowRow(StrictRow):
    depot: str
    work_center: str
    weekly_plan: int = Field(ge=0)
    forecast_output: int = Field(ge=0)
    plan_attainment_pct: Decimal = Field(ge=0, le=200)
    queue_hours: Decimal = Field(ge=0)
    downtime_hours: Decimal = Field(ge=0)
    labor_gap_pct: Decimal = Field(ge=0, le=100)
    constraint_driver: str


class QualityRow(StrictRow):
    depot: str
    work_center: str
    inspections: int = Field(ge=0)
    defect_rate_pct: Decimal = Field(ge=0, le=100)
    first_pass_yield_pct: Decimal = Field(ge=0, le=100)
    open_ncr: int = Field(ge=0)
    repeat_ncr: int = Field(ge=0)
    top_defect: str
    ai_focus: str


class ReadinessTrendRow(StrictRow):
    depot: str
    month: str
    readiness: Decimal = Field(ge=0, le=100)


class WorkforceCapacityRow(StrictRow):
    depot: str
    occupation: str
    assigned_workers: int = Field(ge=0)
    available_workers: int = Field(ge=0)
    required_workers: int = Field(ge=0)
    capacity_gap: int = Field(ge=0)
    training_due: int = Field(ge=0)
    coverage_pct: Decimal = Field(ge=0, le=100)


class WorkforceSourceRow(StrictRow):
    worker_id: str
    depot: str
    onet_soc: str
    occupation: str
    experience_years: Decimal = Field(ge=0)
    shift: str
    availability_pct: Decimal = Field(ge=0, le=100)
    certifications: str
    training_due: str
