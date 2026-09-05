import math
from datetime import datetime
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Float, Select, asc, desc, func, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session

from app.api.contracts import (
    AssessmentKpis,
    AssetKpis,
    AssetResponse,
    CommandKpis,
    ConnectivityAssessmentResponse,
    DepotResponse,
    FlowKpis,
    ImportBatchResponse,
    Page,
    PartResponse,
    ProductionFlowResponse,
    QualityKpis,
    QualityResponse,
    ReadinessDriver,
    ReadinessSummaryResponse,
    ReadinessTrendResponse,
    SupplyKpis,
    WorkforceCapacityResponse,
    WorkforceKpis,
)
from app.auth import CurrentViewer, authorize_depot
from app.db import get_db
from app.models import (
    Asset,
    AssetHealthSnapshot,
    ConnectivityAssessment,
    Depot,
    ImportBatch,
    Manufacturer,
    Occupation,
    Part,
    PartInventorySnapshot,
    ProductionFlowSnapshot,
    QualitySnapshot,
    ReadinessSnapshot,
    ReadinessTrendPoint,
    WorkCenter,
    WorkforceCapacitySnapshot,
    WorkforceSummarySnapshot,
)

router = APIRouter(tags=["readiness"])
DbSession = Annotated[Session, Depends(get_db)]
PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]


def _latest_timestamp(session: Session, model: type[object]) -> datetime:
    observed_at = cast(
        datetime | None,
        session.scalar(select(func.max(model.observed_at))),  # type: ignore[attr-defined]
    )
    if observed_at is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The database has not been seeded",
        )
    return observed_at


def _validate_depot(session: Session, depot: str) -> None:
    if depot != "ALL" and session.get(Depot, depot) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Depot not found")


def _page(
    session: Session, statement: Select[Any], page: int, size: int
) -> tuple[list[Row[Any]], int]:
    total = (
        session.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    )
    items = list(session.execute(statement.offset((page - 1) * size).limit(size)).all())
    return items, int(total)


def _pages(total: int, size: int) -> int:
    return math.ceil(total / size) if total else 0


def _one_decimal(value: Any) -> float:
    return round(float(value), 1)


@router.get("/depots", response_model=list[DepotResponse])
def depots(session: DbSession, principal: CurrentViewer) -> list[DepotResponse]:
    rows = session.execute(select(Depot).order_by(Depot.code)).scalars()
    return [
        DepotResponse(code=row.code, name=row.name, location=row.location)
        for row in rows
        if principal.can_access_depot(row.code)
    ]


@router.get("/assets", response_model=Page[AssetResponse])
def assets(
    session: DbSession,
    principal: CurrentViewer,
    page: PageNumber = 1,
    size: PageSize = 50,
    depot: str = "ALL",
    sort: Literal["risk_desc", "health_asc", "asset_id"] = "risk_desc",
) -> Page[AssetResponse]:
    authorize_depot(principal, depot)
    _validate_depot(session, depot)
    observed_at = _latest_timestamp(session, AssetHealthSnapshot)
    statement = (
        select(
            Asset.asset_id,
            Asset.depot_code,
            Asset.asset_type,
            Manufacturer.name.label("manufacturer"),
            Asset.model,
            Asset.age_years,
            Asset.criticality,
            Asset.connectivity_tier,
            Asset.protocol,
            AssetHealthSnapshot.health_score,
            AssetHealthSnapshot.failure_risk_30d,
            WorkCenter.name.label("work_center"),
            AssetHealthSnapshot.operating_hours,
            AssetHealthSnapshot.observed_at,
        )
        .join(Manufacturer, Manufacturer.id == Asset.manufacturer_id)
        .join(WorkCenter, WorkCenter.id == Asset.work_center_id)
        .join(AssetHealthSnapshot, AssetHealthSnapshot.asset_id == Asset.asset_id)
        .where(AssetHealthSnapshot.observed_at == observed_at)
    )
    if depot != "ALL":
        statement = statement.where(Asset.depot_code == depot)
    ordering: dict[str, Any] = {
        "risk_desc": desc(AssetHealthSnapshot.failure_risk_30d),
        "health_asc": asc(AssetHealthSnapshot.health_score),
        "asset_id": asc(Asset.asset_id),
    }
    statement = statement.order_by(ordering[sort], Asset.asset_id)
    rows, total = _page(session, statement, page, size)
    items = [
        AssetResponse(
            asset_id=row.asset_id,
            depot=row.depot_code,
            asset_type=row.asset_type,
            manufacturer=row.manufacturer,
            model=row.model,
            age_years=float(row.age_years),
            criticality=row.criticality,
            connectivity_tier=row.connectivity_tier,
            protocol=row.protocol,
            health_score=float(row.health_score),
            failure_risk_30d=float(row.failure_risk_30d),
            work_center=row.work_center,
            operating_hours=row.operating_hours,
            observed_at=row.observed_at,
        )
        for row in rows
    ]
    return Page(items=items, page=page, size=size, total=total, pages=_pages(total, size))


@router.get("/workforce/capacity", response_model=Page[WorkforceCapacityResponse])
def workforce_capacity(
    session: DbSession,
    principal: CurrentViewer,
    page: PageNumber = 1,
    size: PageSize = 50,
    depot: str = "ALL",
) -> Page[WorkforceCapacityResponse]:
    authorize_depot(principal, depot)
    _validate_depot(session, depot)
    observed_at = _latest_timestamp(session, WorkforceCapacitySnapshot)
    statement = (
        select(
            WorkforceCapacitySnapshot.depot_code,
            WorkforceCapacitySnapshot.occupation_code,
            Occupation.name.label("occupation"),
            WorkforceCapacitySnapshot.assigned_workers,
            WorkforceCapacitySnapshot.available_workers,
            WorkforceCapacitySnapshot.required_workers,
            WorkforceCapacitySnapshot.capacity_gap,
            WorkforceCapacitySnapshot.training_due,
            WorkforceCapacitySnapshot.coverage_pct,
            WorkforceCapacitySnapshot.observed_at,
        )
        .join(Occupation, Occupation.code == WorkforceCapacitySnapshot.occupation_code)
        .where(WorkforceCapacitySnapshot.observed_at == observed_at)
    )
    if depot != "ALL":
        statement = statement.where(WorkforceCapacitySnapshot.depot_code == depot)
    statement = statement.order_by(WorkforceCapacitySnapshot.coverage_pct, Occupation.name)
    rows, total = _page(session, statement, page, size)
    items = [
        WorkforceCapacityResponse(
            depot=row.depot_code,
            occupation_code=row.occupation_code,
            occupation=row.occupation,
            assigned_workers=row.assigned_workers,
            available_workers=row.available_workers,
            required_workers=row.required_workers,
            capacity_gap=row.capacity_gap,
            training_due=row.training_due,
            coverage_pct=float(row.coverage_pct),
            observed_at=row.observed_at,
        )
        for row in rows
    ]
    return Page(items=items, page=page, size=size, total=total, pages=_pages(total, size))


@router.get("/parts", response_model=Page[PartResponse])
def parts(
    session: DbSession,
    _principal: CurrentViewer,
    page: PageNumber = 1,
    size: PageSize = 50,
    sort: Literal["risk_desc", "lead_desc", "part_id"] = "risk_desc",
) -> Page[PartResponse]:
    observed_at = _latest_timestamp(session, PartInventorySnapshot)
    statement = (
        select(
            Part.part_id,
            Part.fsc,
            Part.part_name,
            Part.source_count,
            Part.lead_time_days,
            PartInventorySnapshot.on_hand,
            PartInventorySnapshot.projected_60d_demand,
            Part.criticality,
            PartInventorySnapshot.supply_risk,
            Part.recommended_action,
            PartInventorySnapshot.scope_key,
            PartInventorySnapshot.observed_at,
        )
        .join(PartInventorySnapshot, PartInventorySnapshot.part_id == Part.part_id)
        .where(PartInventorySnapshot.observed_at == observed_at)
    )
    ordering: dict[str, Any] = {
        "risk_desc": desc(PartInventorySnapshot.supply_risk),
        "lead_desc": desc(Part.lead_time_days),
        "part_id": asc(Part.part_id),
    }
    statement = statement.order_by(ordering[sort], Part.part_id)
    rows, total = _page(session, statement, page, size)
    items = [
        PartResponse(
            part_id=row.part_id,
            fsc=row.fsc,
            part_name=row.part_name,
            source_count=row.source_count,
            lead_time_days=row.lead_time_days,
            on_hand=row.on_hand,
            projected_60d_demand=row.projected_60d_demand,
            criticality=row.criticality,
            supply_risk=float(row.supply_risk),
            recommended_action=row.recommended_action,
            scope=row.scope_key,
            observed_at=row.observed_at,
        )
        for row in rows
    ]
    return Page(items=items, page=page, size=size, total=total, pages=_pages(total, size))


@router.get("/production-flow", response_model=Page[ProductionFlowResponse])
def production_flow(
    session: DbSession,
    principal: CurrentViewer,
    page: PageNumber = 1,
    size: PageSize = 50,
    depot: str = "ALL",
) -> Page[ProductionFlowResponse]:
    authorize_depot(principal, depot)
    _validate_depot(session, depot)
    observed_at = _latest_timestamp(session, ProductionFlowSnapshot)
    statement = (
        select(
            WorkCenter.depot_code,
            WorkCenter.name.label("work_center"),
            ProductionFlowSnapshot.weekly_plan,
            ProductionFlowSnapshot.forecast_output,
            ProductionFlowSnapshot.plan_attainment_pct,
            ProductionFlowSnapshot.queue_hours,
            ProductionFlowSnapshot.downtime_hours,
            ProductionFlowSnapshot.labor_gap_pct,
            ProductionFlowSnapshot.constraint_driver,
            ProductionFlowSnapshot.observed_at,
        )
        .join(WorkCenter, WorkCenter.id == ProductionFlowSnapshot.work_center_id)
        .where(ProductionFlowSnapshot.observed_at == observed_at)
    )
    if depot != "ALL":
        statement = statement.where(WorkCenter.depot_code == depot)
    statement = statement.order_by(ProductionFlowSnapshot.plan_attainment_pct, WorkCenter.name)
    rows, total = _page(session, statement, page, size)
    items = [
        ProductionFlowResponse(
            depot=row.depot_code,
            work_center=row.work_center,
            weekly_plan=row.weekly_plan,
            forecast_output=row.forecast_output,
            plan_attainment_pct=float(row.plan_attainment_pct),
            queue_hours=float(row.queue_hours),
            downtime_hours=float(row.downtime_hours),
            labor_gap_pct=float(row.labor_gap_pct),
            constraint_driver=row.constraint_driver,
            observed_at=row.observed_at,
        )
        for row in rows
    ]
    return Page(items=items, page=page, size=size, total=total, pages=_pages(total, size))


@router.get("/quality", response_model=Page[QualityResponse])
def quality(
    session: DbSession,
    principal: CurrentViewer,
    page: PageNumber = 1,
    size: PageSize = 50,
    depot: str = "ALL",
) -> Page[QualityResponse]:
    authorize_depot(principal, depot)
    _validate_depot(session, depot)
    observed_at = _latest_timestamp(session, QualitySnapshot)
    statement = (
        select(
            WorkCenter.depot_code,
            WorkCenter.name.label("work_center"),
            QualitySnapshot.inspections,
            QualitySnapshot.defect_rate_pct,
            QualitySnapshot.first_pass_yield_pct,
            QualitySnapshot.open_ncr,
            QualitySnapshot.repeat_ncr,
            QualitySnapshot.top_defect,
            QualitySnapshot.ai_focus,
            QualitySnapshot.observed_at,
        )
        .join(WorkCenter, WorkCenter.id == QualitySnapshot.work_center_id)
        .where(QualitySnapshot.observed_at == observed_at)
    )
    if depot != "ALL":
        statement = statement.where(WorkCenter.depot_code == depot)
    statement = statement.order_by(desc(QualitySnapshot.defect_rate_pct), WorkCenter.name)
    rows, total = _page(session, statement, page, size)
    items = [
        QualityResponse(
            depot=row.depot_code,
            work_center=row.work_center,
            inspections=row.inspections,
            defect_rate_pct=float(row.defect_rate_pct),
            first_pass_yield_pct=float(row.first_pass_yield_pct),
            open_ncr=row.open_ncr,
            repeat_ncr=row.repeat_ncr,
            top_defect=row.top_defect,
            ai_focus=row.ai_focus,
            observed_at=row.observed_at,
        )
        for row in rows
    ]
    return Page(items=items, page=page, size=size, total=total, pages=_pages(total, size))


@router.get("/connectivity-assessments", response_model=Page[ConnectivityAssessmentResponse])
def connectivity_assessments(
    session: DbSession,
    principal: CurrentViewer,
    page: PageNumber = 1,
    size: PageSize = 50,
    depot: str = "ALL",
    grade: Literal["Green", "Yellow", "Red"] | None = None,
) -> Page[ConnectivityAssessmentResponse]:
    authorize_depot(principal, depot)
    _validate_depot(session, depot)
    observed_at = _latest_timestamp(session, ConnectivityAssessment)
    statement = (
        select(
            ConnectivityAssessment,
            Asset.depot_code,
            Asset.asset_type,
            Manufacturer.name.label("manufacturer"),
        )
        .join(Asset, Asset.asset_id == ConnectivityAssessment.asset_id)
        .join(Manufacturer, Manufacturer.id == Asset.manufacturer_id)
        .where(ConnectivityAssessment.observed_at == observed_at)
    )
    if depot != "ALL":
        statement = statement.where(Asset.depot_code == depot)
    if grade is not None:
        statement = statement.where(ConnectivityAssessment.readiness_grade == grade)
    statement = statement.order_by(
        ConnectivityAssessment.readiness_score, ConnectivityAssessment.asset_id
    )
    rows, total = _page(session, statement, page, size)
    items = [
        ConnectivityAssessmentResponse(
            asset_id=row.ConnectivityAssessment.asset_id,
            depot=row.depot_code,
            asset_type=row.asset_type,
            manufacturer=row.manufacturer,
            connectivity=row.ConnectivityAssessment.connectivity_label,
            protocol=row.ConnectivityAssessment.protocol_label,
            data_rights=row.ConnectivityAssessment.data_rights_label,
            cyber_status=row.ConnectivityAssessment.cyber_status_label,
            history=row.ConnectivityAssessment.history_label,
            data_quality=row.ConnectivityAssessment.data_quality_label,
            readiness_score=row.ConnectivityAssessment.readiness_score,
            readiness_grade=row.ConnectivityAssessment.readiness_grade,
            recommended_action=row.ConnectivityAssessment.recommended_action,
            dimension_points=row.ConnectivityAssessment.dimension_points,
            ruleset=row.ConnectivityAssessment.ruleset_code,
            observed_at=row.ConnectivityAssessment.observed_at,
        )
        for row in rows
    ]
    return Page(items=items, page=page, size=size, total=total, pages=_pages(total, size))


@router.get("/readiness/trend", response_model=list[ReadinessTrendResponse])
def readiness_trend(
    session: DbSession, principal: CurrentViewer, depot: str = "ALL"
) -> list[ReadinessTrendResponse]:
    authorize_depot(principal, depot)
    _validate_depot(session, depot)
    if depot == "ALL":
        statement = (
            select(
                ReadinessTrendPoint.reporting_period,
                func.min(ReadinessTrendPoint.display_month).label("month"),
                func.avg(ReadinessTrendPoint.readiness_score).label("readiness"),
            )
            .group_by(ReadinessTrendPoint.reporting_period)
            .order_by(ReadinessTrendPoint.reporting_period)
        )
    else:
        statement = (
            select(
                ReadinessTrendPoint.reporting_period,
                ReadinessTrendPoint.display_month.label("month"),
                ReadinessTrendPoint.readiness_score.label("readiness"),
            )
            .where(ReadinessTrendPoint.depot_code == depot)
            .order_by(ReadinessTrendPoint.reporting_period)
        )
    return [
        ReadinessTrendResponse(
            reporting_period=row.reporting_period,
            month=row.month,
            readiness=round(float(row.readiness), 1),
        )
        for row in session.execute(statement).all()
    ]


@router.get("/readiness/summary", response_model=ReadinessSummaryResponse)
def readiness_summary(
    session: DbSession, principal: CurrentViewer, depot: str = "ALL"
) -> ReadinessSummaryResponse:
    authorize_depot(principal, depot)
    _validate_depot(session, depot)
    asset_at = _latest_timestamp(session, AssetHealthSnapshot)
    workforce_at = _latest_timestamp(session, WorkforceCapacitySnapshot)
    flow_at = _latest_timestamp(session, ProductionFlowSnapshot)
    quality_at = _latest_timestamp(session, QualitySnapshot)
    supply_at = _latest_timestamp(session, PartInventorySnapshot)
    assessment_at = _latest_timestamp(session, ConnectivityAssessment)
    readiness_at = _latest_timestamp(session, ReadinessSnapshot)

    asset_filter = () if depot == "ALL" else (Asset.depot_code == depot,)
    workforce_filter = () if depot == "ALL" else (WorkforceCapacitySnapshot.depot_code == depot,)
    workforce_summary_filter = (
        () if depot == "ALL" else (WorkforceSummarySnapshot.depot_code == depot,)
    )
    center_filter = () if depot == "ALL" else (WorkCenter.depot_code == depot,)
    readiness_filter = () if depot == "ALL" else (ReadinessSnapshot.depot_code == depot,)

    asset_values = session.execute(
        select(
            func.count(Asset.asset_id),
            func.avg(sql_cast(AssetHealthSnapshot.health_score, Float)),
            func.avg(sql_cast(AssetHealthSnapshot.failure_risk_30d, Float)),
            func.count().filter(AssetHealthSnapshot.failure_risk_30d >= 50),
            func.count().filter(AssetHealthSnapshot.failure_risk_30d >= 70),
            func.count().filter(Asset.connectivity_tier == "Legacy Analog"),
        )
        .join(AssetHealthSnapshot, AssetHealthSnapshot.asset_id == Asset.asset_id)
        .where(AssetHealthSnapshot.observed_at == asset_at, *asset_filter)
    ).one()
    workforce_values = session.execute(
        select(
            func.coalesce(func.sum(WorkforceSummarySnapshot.worker_count), 0),
            func.sum(
                WorkforceSummarySnapshot.average_availability_pct
                * WorkforceSummarySnapshot.worker_count
            )
            / func.nullif(func.sum(WorkforceSummarySnapshot.worker_count), 0),
            func.coalesce(func.sum(WorkforceSummarySnapshot.training_due_count), 0),
        ).where(
            WorkforceSummarySnapshot.observed_at == workforce_at,
            *workforce_summary_filter,
        )
    ).one()
    capacity_values = session.execute(
        select(
            func.coalesce(
                func.sum(
                    func.greatest(
                        WorkforceCapacitySnapshot.required_workers
                        - WorkforceCapacitySnapshot.available_workers,
                        0,
                    )
                ),
                0,
            ),
            func.count().filter(WorkforceCapacitySnapshot.coverage_pct < 80),
        ).where(
            WorkforceCapacitySnapshot.observed_at == workforce_at,
            *workforce_filter,
        )
    ).one()
    flow_values = session.execute(
        select(
            func.avg(sql_cast(ProductionFlowSnapshot.plan_attainment_pct, Float)),
            func.count().filter(ProductionFlowSnapshot.constraint_driver != "None"),
            func.coalesce(func.sum(sql_cast(ProductionFlowSnapshot.queue_hours, Float)), 0),
            func.coalesce(func.sum(sql_cast(ProductionFlowSnapshot.downtime_hours, Float)), 0),
        )
        .join(WorkCenter, WorkCenter.id == ProductionFlowSnapshot.work_center_id)
        .where(ProductionFlowSnapshot.observed_at == flow_at, *center_filter)
    ).one()
    quality_values = session.execute(
        select(
            func.coalesce(func.sum(QualitySnapshot.inspections), 0),
            func.avg(sql_cast(QualitySnapshot.defect_rate_pct, Float)),
            func.avg(sql_cast(QualitySnapshot.first_pass_yield_pct, Float)),
            func.coalesce(func.sum(QualitySnapshot.open_ncr), 0),
        )
        .join(WorkCenter, WorkCenter.id == QualitySnapshot.work_center_id)
        .where(QualitySnapshot.observed_at == quality_at, *center_filter)
    ).one()
    supply_values = session.execute(
        select(
            func.count(Part.part_id),
            func.count().filter(PartInventorySnapshot.supply_risk >= 70),
            func.count().filter(Part.source_count == 1),
            func.avg(Part.lead_time_days),
        )
        .join(PartInventorySnapshot, PartInventorySnapshot.part_id == Part.part_id)
        .where(
            PartInventorySnapshot.observed_at == supply_at,
            PartInventorySnapshot.scope_key == "GLOBAL",
        )
    ).one()
    assessment_values = session.execute(
        select(
            func.count().filter(ConnectivityAssessment.readiness_grade == "Green"),
            func.count().filter(ConnectivityAssessment.readiness_grade == "Yellow"),
            func.count().filter(ConnectivityAssessment.readiness_grade == "Red"),
            func.min(ConnectivityAssessment.ruleset_code),
        )
        .join(Asset, Asset.asset_id == ConnectivityAssessment.asset_id)
        .where(ConnectivityAssessment.observed_at == assessment_at, *asset_filter)
    ).one()
    readiness_value, source_system = session.execute(
        select(
            func.avg(ReadinessSnapshot.readiness_score),
            func.min(ReadinessSnapshot.source_system),
        ).where(ReadinessSnapshot.observed_at == readiness_at, *readiness_filter)
    ).one()

    plan_attainment = _one_decimal(flow_values[0])
    open_ncr = int(quality_values[3])
    drivers = sorted(
        [
            ReadinessDriver(
                name="Workforce Capacity", value=min(100, float(capacity_values[0]) / 4 + 35)
            ),
            ReadinessDriver(
                name="Supply Chain", value=min(100, float(supply_values[1]) / 8 + 30)
            ),
            ReadinessDriver(name="Asset Availability", value=float(asset_values[2])),
            ReadinessDriver(name="Production Flow", value=100 - plan_attainment),
            ReadinessDriver(name="Quality/Rework", value=min(100, open_ncr / 15)),
        ],
        key=lambda driver: driver.value,
        reverse=True,
    )
    return ReadinessSummaryResponse(
        depot=depot,
        command=CommandKpis(
            composite_readiness=_one_decimal(readiness_value),
            assets_elevated=int(asset_values[3]),
            workforce_gap=int(capacity_values[0]),
            critical_supply=int(supply_values[1]),
            plan_attainment=plan_attainment,
            open_ncr=open_ncr,
            bottlenecks=int(flow_values[1]),
        ),
        assets=AssetKpis(
            count=int(asset_values[0]),
            average_health=_one_decimal(asset_values[1]),
            high_risk=int(asset_values[4]),
            legacy_analog=int(asset_values[5]),
        ),
        workforce=WorkforceKpis(
            count=int(workforce_values[0]),
            average_availability=_one_decimal(workforce_values[1]),
            skill_families_at_risk=int(capacity_values[1]),
            training_due=int(workforce_values[2]),
        ),
        flow=FlowKpis(
            plan_attainment=plan_attainment,
            bottlenecks=int(flow_values[1]),
            queue_hours=_one_decimal(flow_values[2]),
            downtime_hours=_one_decimal(flow_values[3]),
        ),
        quality=QualityKpis(
            inspections=int(quality_values[0]),
            average_defect_rate=_one_decimal(quality_values[1]),
            first_pass_yield=_one_decimal(quality_values[2]),
            open_ncr=open_ncr,
        ),
        supply=SupplyKpis(
            parts=int(supply_values[0]),
            critical_risks=int(supply_values[1]),
            single_source=int(supply_values[2]),
            average_lead_time_days=round(float(supply_values[3])),
            scope="GLOBAL",
        ),
        assessment=AssessmentKpis(
            green=int(assessment_values[0]),
            yellow=int(assessment_values[1]),
            red=int(assessment_values[2]),
            ruleset=str(assessment_values[3]),
        ),
        drivers=drivers,
        observed_at=readiness_at,
        source_system=str(source_system),
    )


@router.get("/imports/latest", response_model=ImportBatchResponse)
def latest_import(session: DbSession, _principal: CurrentViewer) -> ImportBatchResponse:
    batch = session.scalar(
        select(ImportBatch)
        .where(ImportBatch.status == "SUCCEEDED")
        .order_by(desc(ImportBatch.completed_at))
        .limit(1)
    )
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No import found")
    return ImportBatchResponse(
        id=str(batch.id),
        dataset_version=batch.dataset_version,
        schema_version=batch.schema_version,
        status=batch.status,
        manifest_sha256=batch.manifest_sha256,
        row_counts=batch.row_counts,
        rejection_count=batch.rejection_count,
        started_at=batch.started_at,
        completed_at=batch.completed_at,
    )
