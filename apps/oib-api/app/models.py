from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Depot(Base):
    __tablename__ = "depots"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    location: Mapped[str] = mapped_column(String(160), nullable=False)


class DataSource(Base):
    __tablename__ = "data_sources"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_code: Mapped[str] = mapped_column(ForeignKey("data_sources.code"), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    row_counts: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    rejection_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    __table_args__ = (
        CheckConstraint(
            "status IN ('RUNNING', 'SUCCEEDED', 'FAILED')", name="import_batches_status_check"
        ),
        Index(
            "uq_import_batches_succeeded_manifest",
            "manifest_sha256",
            unique=True,
            postgresql_where=text("status = 'SUCCEEDED'"),
        ),
    )


class ImportRejection(Base):
    __tablename__ = "import_rejections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    dataset: Mapped[str] = mapped_column(String(64), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(128))
    raw_value: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class ScoringRuleVersion(Base):
    __tablename__ = "scoring_rule_versions"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    rules: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Manufacturer(Base):
    __tablename__ = "manufacturers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)


class WorkCenter(Base):
    __tablename__ = "work_centers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    depot_code: Mapped[str] = mapped_column(ForeignKey("depots.code"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    __table_args__ = (UniqueConstraint("depot_code", "name"),)


class Occupation(Base):
    __tablename__ = "occupations"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)


class Asset(TimestampMixin, Base):
    __tablename__ = "assets"

    asset_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    depot_code: Mapped[str] = mapped_column(ForeignKey("depots.code"), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(120), nullable=False)
    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("manufacturers.id"), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    age_years: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    criticality: Mapped[str] = mapped_column(String(16), nullable=False)
    connectivity_tier: Mapped[str] = mapped_column(String(32), nullable=False)
    protocol: Mapped[str] = mapped_column(String(64), nullable=False)
    work_center_id: Mapped[int] = mapped_column(ForeignKey("work_centers.id"), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    import_batch_id: Mapped[UUID] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    __table_args__ = (
        CheckConstraint(
            "criticality IN ('Low', 'Medium', 'High')", name="assets_criticality_check"
        ),
        Index("ix_assets_depot", "depot_code"),
    )


class AssetHealthSnapshot(Base):
    __tablename__ = "asset_health_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.asset_id"), nullable=False)
    health_score: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    failure_risk_30d: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    operating_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    import_batch_id: Mapped[UUID] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    __table_args__ = (
        UniqueConstraint("asset_id", "observed_at"),
        CheckConstraint(
            "health_score BETWEEN 0 AND 100", name="asset_health_snapshots_health_score_check"
        ),
        CheckConstraint(
            "failure_risk_30d BETWEEN 0 AND 100",
            name="asset_health_snapshots_failure_risk_30d_check",
        ),
        Index("ix_asset_health_risk", "failure_risk_30d"),
    )


class WorkforceSummarySnapshot(Base):
    __tablename__ = "workforce_summary_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    depot_code: Mapped[str] = mapped_column(ForeignKey("depots.code"), nullable=False)
    worker_count: Mapped[int] = mapped_column(Integer, nullable=False)
    average_availability_pct: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    training_due_count: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    import_batch_id: Mapped[UUID] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint("depot_code", "observed_at"),
        CheckConstraint(
            "average_availability_pct BETWEEN 0 AND 100",
            name="workforce_summary_snapshots_average_availability_pct_check",
        ),
    )


class WorkforceCapacitySnapshot(Base):
    __tablename__ = "workforce_capacity_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    depot_code: Mapped[str] = mapped_column(ForeignKey("depots.code"), nullable=False)
    occupation_code: Mapped[str] = mapped_column(ForeignKey("occupations.code"), nullable=False)
    assigned_workers: Mapped[int] = mapped_column(Integer, nullable=False)
    available_workers: Mapped[int] = mapped_column(Integer, nullable=False)
    required_workers: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity_gap: Mapped[int] = mapped_column(Integer, nullable=False)
    training_due: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage_pct: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    import_batch_id: Mapped[UUID] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint("depot_code", "occupation_code", "observed_at"),
        CheckConstraint(
            "coverage_pct BETWEEN 0 AND 100",
            name="workforce_capacity_snapshots_coverage_pct_check",
        ),
        Index("ix_workforce_capacity_depot", "depot_code"),
    )


class Part(TimestampMixin, Base):
    __tablename__ = "parts"

    part_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    fsc: Mapped[str] = mapped_column(String(8), nullable=False)
    part_name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    criticality: Mapped[str] = mapped_column(String(16), nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(160), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    import_batch_id: Mapped[UUID] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    __table_args__ = (
        CheckConstraint(
            "criticality IN ('Low', 'Medium', 'High', 'Critical')",
            name="parts_criticality_check",
        ),
    )


class PartInventorySnapshot(Base):
    __tablename__ = "part_inventory_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    part_id: Mapped[str] = mapped_column(ForeignKey("parts.part_id"), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(16), nullable=False)
    depot_code: Mapped[str | None] = mapped_column(ForeignKey("depots.code"))
    on_hand: Mapped[int] = mapped_column(Integer, nullable=False)
    projected_60d_demand: Mapped[int] = mapped_column(Integer, nullable=False)
    supply_risk: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    import_batch_id: Mapped[UUID] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint("part_id", "scope_key", "observed_at"),
        CheckConstraint(
            "supply_risk BETWEEN 0 AND 100", name="part_inventory_snapshots_supply_risk_check"
        ),
        CheckConstraint(
            "(scope_key = 'GLOBAL' AND depot_code IS NULL) OR scope_key = depot_code",
            name="part_inventory_snapshots_check",
        ),
        Index("ix_part_inventory_scope_risk", "scope_key", "supply_risk"),
    )


class ProductionFlowSnapshot(Base):
    __tablename__ = "production_flow_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_center_id: Mapped[int] = mapped_column(ForeignKey("work_centers.id"), nullable=False)
    weekly_plan: Mapped[int] = mapped_column(Integer, nullable=False)
    forecast_output: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_attainment_pct: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    queue_hours: Mapped[Decimal] = mapped_column(Numeric(8, 1), nullable=False)
    downtime_hours: Mapped[Decimal] = mapped_column(Numeric(8, 1), nullable=False)
    labor_gap_pct: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    constraint_driver: Mapped[str] = mapped_column(String(160), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    import_batch_id: Mapped[UUID] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint("work_center_id", "observed_at"),
        CheckConstraint(
            "plan_attainment_pct BETWEEN 0 AND 200",
            name="production_flow_snapshots_plan_attainment_pct_check",
        ),
        Index("ix_production_flow_center", "work_center_id"),
    )


class QualitySnapshot(Base):
    __tablename__ = "quality_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_center_id: Mapped[int] = mapped_column(ForeignKey("work_centers.id"), nullable=False)
    inspections: Mapped[int] = mapped_column(Integer, nullable=False)
    defect_rate_pct: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    first_pass_yield_pct: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    open_ncr: Mapped[int] = mapped_column(Integer, nullable=False)
    repeat_ncr: Mapped[int] = mapped_column(Integer, nullable=False)
    top_defect: Mapped[str] = mapped_column(String(160), nullable=False)
    ai_focus: Mapped[str] = mapped_column(String(160), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    import_batch_id: Mapped[UUID] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint("work_center_id", "observed_at"),
        CheckConstraint(
            "defect_rate_pct BETWEEN 0 AND 100", name="quality_snapshots_defect_rate_pct_check"
        ),
        CheckConstraint(
            "first_pass_yield_pct BETWEEN 0 AND 100",
            name="quality_snapshots_first_pass_yield_pct_check",
        ),
        Index("ix_quality_center", "work_center_id"),
    )


class ConnectivityAssessment(Base):
    __tablename__ = "connectivity_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.asset_id"), nullable=False)
    ruleset_code: Mapped[str] = mapped_column(
        ForeignKey("scoring_rule_versions.code"), nullable=False
    )
    connectivity_code: Mapped[str] = mapped_column(String(64), nullable=False)
    connectivity_label: Mapped[str] = mapped_column(String(64), nullable=False)
    protocol_code: Mapped[str] = mapped_column(String(64), nullable=False)
    protocol_label: Mapped[str] = mapped_column(String(64), nullable=False)
    data_rights_code: Mapped[str] = mapped_column(String(64), nullable=False)
    data_rights_label: Mapped[str] = mapped_column(String(64), nullable=False)
    cyber_status_code: Mapped[str] = mapped_column(String(64), nullable=False)
    cyber_status_label: Mapped[str] = mapped_column(String(64), nullable=False)
    history_code: Mapped[str] = mapped_column(String(64), nullable=False)
    history_label: Mapped[str] = mapped_column(String(64), nullable=False)
    data_quality_code: Mapped[str] = mapped_column(String(64), nullable=False)
    data_quality_label: Mapped[str] = mapped_column(String(64), nullable=False)
    dimension_points: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    readiness_score: Mapped[int] = mapped_column(Integer, nullable=False)
    readiness_grade: Mapped[str] = mapped_column(String(16), nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(200), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    import_batch_id: Mapped[UUID] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    __table_args__ = (
        UniqueConstraint("asset_id", "ruleset_code", "observed_at"),
        CheckConstraint(
            "readiness_score BETWEEN 0 AND 100",
            name="connectivity_assessments_readiness_score_check",
        ),
        CheckConstraint(
            "readiness_grade IN ('Green', 'Yellow', 'Red')",
            name="connectivity_assessments_readiness_grade_check",
        ),
        Index("ix_connectivity_grade", "readiness_grade"),
    )


class SubmittedConnectivityAssessment(Base):
    """User-entered assessment whose score is calculated by the API."""

    __tablename__ = "submitted_connectivity_assessments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    asset_id: Mapped[str] = mapped_column(String(32), nullable=False)
    depot_code: Mapped[str] = mapped_column(String(16), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(120), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    connectivity_code: Mapped[str] = mapped_column(String(64), nullable=False)
    connectivity_label: Mapped[str] = mapped_column(String(64), nullable=False)
    protocol_code: Mapped[str] = mapped_column(String(64), nullable=False)
    protocol_label: Mapped[str] = mapped_column(String(64), nullable=False)
    data_rights_code: Mapped[str] = mapped_column(String(64), nullable=False)
    data_rights_label: Mapped[str] = mapped_column(String(64), nullable=False)
    cyber_status_code: Mapped[str] = mapped_column(String(64), nullable=False)
    cyber_status_label: Mapped[str] = mapped_column(String(64), nullable=False)
    history_code: Mapped[str] = mapped_column(String(64), nullable=False)
    history_label: Mapped[str] = mapped_column(String(64), nullable=False)
    data_quality_code: Mapped[str] = mapped_column(String(64), nullable=False)
    data_quality_label: Mapped[str] = mapped_column(String(64), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    dimension_points: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    readiness_score: Mapped[int] = mapped_column(Integer, nullable=False)
    readiness_grade: Mapped[str] = mapped_column(String(16), nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(200), nullable=False)
    ruleset_code: Mapped[str] = mapped_column(
        ForeignKey("scoring_rule_versions.code"), nullable=False
    )
    actor_subject: Mapped[str] = mapped_column(String(256), nullable=False)
    idempotency_key: Mapped[UUID] = mapped_column(nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    __table_args__ = (
        UniqueConstraint("actor_subject", "idempotency_key"),
        CheckConstraint(
            "depot_code IN ('RRAD', 'ANAD', 'SIAD', 'WVA', 'Other')",
            name="submitted_assessments_depot_check",
        ),
        CheckConstraint(
            "readiness_score BETWEEN 0 AND 100",
            name="submitted_assessments_score_check",
        ),
        CheckConstraint(
            "readiness_grade IN ('Green', 'Yellow', 'Red')",
            name="submitted_assessments_grade_check",
        ),
        Index("ix_submitted_assessments_depot_time", "depot_code", "assessed_at"),
    )


class AuditEvent(Base):
    """Security-safe audit event. Sensitive assessment notes are deliberately excluded."""

    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actor_subject: Mapped[str] = mapped_column(String(256), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    depot_code: Mapped[str | None] = mapped_column(String(16))
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_data: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('SUCCEEDED', 'DENIED', 'FAILED')", name="audit_events_outcome_check"
        ),
        Index("ix_audit_events_time", "occurred_at"),
        Index("ix_audit_events_actor", "actor_subject"),
    )


class ReadinessSnapshot(Base):
    __tablename__ = "readiness_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    depot_code: Mapped[str] = mapped_column(ForeignKey("depots.code"), nullable=False)
    readiness_score: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    top_drivers: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    import_batch_id: Mapped[UUID] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint("depot_code", "observed_at"),
        CheckConstraint(
            "readiness_score BETWEEN 0 AND 100", name="readiness_snapshots_readiness_score_check"
        ),
    )


class ReadinessTrendPoint(Base):
    __tablename__ = "readiness_trend_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    depot_code: Mapped[str] = mapped_column(ForeignKey("depots.code"), nullable=False)
    reporting_period: Mapped[date] = mapped_column(Date, nullable=False)
    display_month: Mapped[str] = mapped_column(String(8), nullable=False)
    readiness_score: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    import_batch_id: Mapped[UUID] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint("depot_code", "reporting_period"),
        CheckConstraint(
            "readiness_score BETWEEN 0 AND 100",
            name="readiness_trend_points_readiness_score_check",
        ),
        Index("ix_readiness_trend_period", "reporting_period"),
    )
