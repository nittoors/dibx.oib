from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient
from pytest import mark
from sqlalchemy import delete, select

from app.auth import ASSESSOR_GROUP, Principal, get_current_principal
from app.db import SessionLocal
from app.main import app
from app.models import AuditEvent, SubmittedConnectivityAssessment

pytestmark = mark.anyio


def assessment_payload(**changes: str) -> dict[str, str]:
    payload = {
        "asset_id": "TEST-CNC-999",
        "depot": "RRAD",
        "asset_type": "CNC",
        "manufacturer": "Test Manufacturer",
        "connectivity": "Native Digital",
        "protocol": "MTConnect",
        "data_rights": "Government usable",
        "cyber_status": "Approved",
        "history": ">24 months",
        "data_quality": "Good",
        "notes": "test-only note that must not enter the audit metadata",
    }
    return {**payload, **changes}


def cleanup(idempotency_key: UUID, subject: str = "local-reviewer") -> None:
    with SessionLocal.begin() as session:
        row = session.scalar(
            select(SubmittedConnectivityAssessment).where(
                SubmittedConnectivityAssessment.actor_subject == subject,
                SubmittedConnectivityAssessment.idempotency_key == idempotency_key,
            )
        )
        if row is not None:
            session.execute(delete(AuditEvent).where(AuditEvent.resource_id == str(row.id)))
            session.delete(row)


async def test_api_scores_persists_audits_and_idempotently_returns_the_same_record() -> None:
    key = uuid4()
    headers = {"Idempotency-Key": str(key), "X-Request-ID": "phase4-test-request"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            first = await client.post(
                "/api/v1/connectivity-assessments",
                json=assessment_payload(),
                headers=headers,
            )
            second = await client.post(
                "/api/v1/connectivity-assessments",
                json=assessment_payload(notes="a changed retry body"),
                headers=headers,
            )
            submitted = await client.get("/api/v1/connectivity-assessments/submitted")
            audit = await client.get("/api/v1/audit-events")

        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["id"] == second.json()["id"]
        assert first.json()["readiness_score"] == 100
        assert first.json()["readiness_grade"] == "Green"
        assert first.json()["ruleset"] == "prototype-v1"
        assert first.headers["cache-control"] == "no-store"
        assert first.headers["x-content-type-options"] == "nosniff"
        assert first.headers["x-frame-options"] == "DENY"
        assert submitted.status_code == 200
        assert any(item["id"] == first.json()["id"] for item in submitted.json()["items"])
        assert audit.status_code == 200
        assert any(item["resource_id"] == first.json()["id"] for item in audit.json()["items"])
        with SessionLocal() as session:
            row = session.scalar(
                select(SubmittedConnectivityAssessment).where(
                    SubmittedConnectivityAssessment.actor_subject == "local-reviewer",
                    SubmittedConnectivityAssessment.idempotency_key == key,
                )
            )
            assert row is not None
            events = session.scalars(
                select(AuditEvent).where(AuditEvent.resource_id == str(row.id))
            ).all()
            assert len(events) == 1
            assert events[0].request_id == "phase4-test-request"
            assert "notes" not in events[0].event_data
            assert "test-only" not in str(events[0].event_data)
    finally:
        cleanup(key)


async def test_assessment_input_is_bounded_and_server_computed() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/connectivity-assessments",
            json={**assessment_payload(notes="x" * 4001), "readiness_score": 0},
            headers={"Idempotency-Key": str(uuid4())},
        )
        client_score = await client.post(
            "/api/v1/connectivity-assessments",
            json={**assessment_payload(), "readiness_score": 0},
            headers={"Idempotency-Key": str(uuid4())},
        )

    assert response.status_code == 422
    assert client_score.status_code == 422


async def test_viewer_cannot_write_and_assessor_cannot_cross_depot_scope() -> None:
    viewer = Principal(
        subject="phase4-viewer",
        groups=frozenset({"OIB-Viewers"}),
        depots=frozenset({"RRAD"}),
        authentication_mode="cognito",
    )
    app.dependency_overrides[get_current_principal] = lambda: viewer
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            denied_role = await client.post(
                "/api/v1/connectivity-assessments",
                json=assessment_payload(),
                headers={"Idempotency-Key": str(uuid4())},
            )
        assert denied_role.status_code == 403

        assessor = Principal(
            subject="phase4-assessor",
            groups=frozenset({ASSESSOR_GROUP}),
            depots=frozenset({"ANAD"}),
            authentication_mode="cognito",
        )
        app.dependency_overrides[get_current_principal] = lambda: assessor
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            denied_depot = await client.post(
                "/api/v1/connectivity-assessments",
                json=assessment_payload(depot="RRAD"),
                headers={"Idempotency-Key": str(uuid4())},
            )
            denied_all = await client.get(
                "/api/v1/connectivity-assessments/submitted", params={"depot": "ALL"}
            )
        assert denied_depot.status_code == 403
        assert denied_all.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_principal, None)
