import math
from datetime import UTC, date, datetime
from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.contracts import (
    AuditEventResponse,
    Page,
    SubmittedAssessmentRequest,
    SubmittedAssessmentResponse,
)
from app.auth import CurrentAdmin, CurrentAssessor, CurrentViewer, authorize_depot
from app.db import get_db
from app.models import AuditEvent, ScoringRuleVersion, SubmittedConnectivityAssessment
from app.scoring import ScoringRules, score_assessment

router = APIRouter(tags=["assessments"])
DbSession = Annotated[Session, Depends(get_db)]
IdempotencyKey = Annotated[UUID, Header(alias="Idempotency-Key")]


def _response(row: SubmittedConnectivityAssessment) -> SubmittedAssessmentResponse:
    return SubmittedAssessmentResponse(
        id=row.id,
        asset_id=row.asset_id,
        depot=row.depot_code,
        asset_type=row.asset_type,
        manufacturer=row.manufacturer,
        connectivity=row.connectivity_label,
        protocol=row.protocol_label,
        data_rights=row.data_rights_label,
        cyber_status=row.cyber_status_label,
        history=row.history_label,
        data_quality=row.data_quality_label,
        notes=row.notes,
        readiness_score=row.readiness_score,
        readiness_grade=cast(Literal["Green", "Yellow", "Red"], row.readiness_grade),
        recommended_action=row.recommended_action,
        dimension_points=row.dimension_points,
        ruleset=row.ruleset_code,
        assessed_at=row.assessed_at,
    )


@router.post(
    "/connectivity-assessments",
    response_model=SubmittedAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assessment(
    payload: SubmittedAssessmentRequest,
    idempotency_key: IdempotencyKey,
    request: Request,
    session: DbSession,
    principal: CurrentAssessor,
) -> SubmittedAssessmentResponse:
    authorize_depot(principal, payload.depot)
    existing = session.scalar(
        select(SubmittedConnectivityAssessment).where(
            SubmittedConnectivityAssessment.actor_subject == principal.subject,
            SubmittedConnectivityAssessment.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return _response(existing)

    rule_version = session.scalar(
        select(ScoringRuleVersion)
        .where(ScoringRuleVersion.effective_from <= date.today())
        .order_by(desc(ScoringRuleVersion.effective_from), desc(ScoringRuleVersion.code))
        .limit(1)
    )
    if rule_version is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scoring rules are unavailable",
        )
    rules = ScoringRules.model_validate(rule_version.rules)
    scoring_values: dict[str, str] = {
        "connectivity": payload.connectivity,
        "protocol": payload.protocol,
        "data_rights": payload.data_rights,
        "cyber_status": payload.cyber_status,
        "history": payload.history,
        "data_quality": payload.data_quality,
    }
    result = score_assessment(scoring_values, rules)
    assessed_at = datetime.now(UTC)
    row = SubmittedConnectivityAssessment(
        asset_id=payload.asset_id,
        depot_code=payload.depot,
        asset_type=payload.asset_type,
        manufacturer=payload.manufacturer,
        connectivity_code=result.canonical_values["connectivity"],
        connectivity_label=payload.connectivity,
        protocol_code=result.canonical_values["protocol"],
        protocol_label=payload.protocol,
        data_rights_code=result.canonical_values["data_rights"],
        data_rights_label=payload.data_rights,
        cyber_status_code=result.canonical_values["cyber_status"],
        cyber_status_label=payload.cyber_status,
        history_code=result.canonical_values["history"],
        history_label=payload.history,
        data_quality_code=result.canonical_values["data_quality"],
        data_quality_label=payload.data_quality,
        notes=payload.notes,
        dimension_points=result.dimension_points,
        readiness_score=result.score,
        readiness_grade=result.grade,
        recommended_action=result.recommended_action,
        ruleset_code=rule_version.code,
        actor_subject=principal.subject,
        idempotency_key=idempotency_key,
        assessed_at=assessed_at,
    )
    session.add(row)
    session.flush()
    session.add(
        AuditEvent(
            actor_subject=principal.subject,
            action="connectivity_assessment.created",
            resource_type="connectivity_assessment",
            resource_id=str(row.id),
            outcome="SUCCEEDED",
            depot_code=payload.depot,
            request_id=request.state.request_id,
            event_data={
                "asset_id": payload.asset_id,
                "readiness_grade": result.grade,
                "ruleset": rule_version.code,
            },
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        concurrent = session.scalar(
            select(SubmittedConnectivityAssessment).where(
                SubmittedConnectivityAssessment.actor_subject == principal.subject,
                SubmittedConnectivityAssessment.idempotency_key == idempotency_key,
            )
        )
        if concurrent is None:
            raise
        return _response(concurrent)
    session.refresh(row)
    return _response(row)


@router.get(
    "/connectivity-assessments/submitted",
    response_model=Page[SubmittedAssessmentResponse],
)
def submitted_assessments(
    session: DbSession,
    principal: CurrentViewer,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 80,
    depot: str = "ALL",
) -> Page[SubmittedAssessmentResponse]:
    authorize_depot(principal, depot)
    statement = select(SubmittedConnectivityAssessment)
    if not principal.is_admin:
        statement = statement.where(
            SubmittedConnectivityAssessment.actor_subject == principal.subject
        )
    if depot != "ALL":
        statement = statement.where(SubmittedConnectivityAssessment.depot_code == depot)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = session.scalars(
        statement.order_by(
            desc(SubmittedConnectivityAssessment.assessed_at),
            desc(SubmittedConnectivityAssessment.id),
        )
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return Page(
        items=[_response(row) for row in rows],
        page=page,
        size=size,
        total=int(total),
        pages=math.ceil(total / size) if total else 0,
    )


@router.get("/audit-events", response_model=Page[AuditEventResponse])
def audit_events(
    session: DbSession,
    _principal: CurrentAdmin,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> Page[AuditEventResponse]:
    total = session.scalar(select(func.count()).select_from(AuditEvent)) or 0
    rows = session.scalars(
        select(AuditEvent)
        .order_by(desc(AuditEvent.occurred_at), desc(AuditEvent.id))
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    items = [
        AuditEventResponse(
            id=row.id,
            occurred_at=row.occurred_at,
            actor_subject=row.actor_subject,
            action=row.action,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            outcome=row.outcome,
            depot=row.depot_code,
            request_id=row.request_id,
            metadata=row.event_data,
        )
        for row in rows
    ]
    return Page(
        items=items,
        page=page,
        size=size,
        total=int(total),
        pages=math.ceil(total / size) if total else 0,
    )
