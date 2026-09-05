from httpx import ASGITransport, AsyncClient
from pytest import mark

from app.main import app

pytestmark = mark.anyio


async def test_read_endpoints_expose_seeded_operational_data() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        depots = await client.get("/api/v1/depots")
        assets = await client.get("/api/v1/assets", params={"depot": "RRAD", "size": 2})
        workforce = await client.get("/api/v1/workforce/capacity", params={"size": 2})
        parts = await client.get("/api/v1/parts", params={"sort": "lead_desc", "size": 2})
        flow = await client.get("/api/v1/production-flow", params={"depot": "ANAD", "size": 2})
        quality = await client.get("/api/v1/quality", params={"depot": "SIAD", "size": 2})
        assessments = await client.get(
            "/api/v1/connectivity-assessments", params={"grade": "Green", "size": 2}
        )
        trend = await client.get("/api/v1/readiness/trend", params={"depot": "WVA"})
        latest_import = await client.get("/api/v1/imports/latest")

    assert [row["code"] for row in depots.json()] == ["ANAD", "RRAD", "SIAD", "WVA"]
    assert assets.json()["total"] == 400
    assert len(assets.json()["items"]) == 2
    assert workforce.json()["total"] == 40
    assert parts.json()["total"] == 1200
    assert flow.json()["total"] == 10
    assert quality.json()["total"] == 10
    assert assessments.json()["total"] == 64
    assert len(trend.json()) == 6
    assert latest_import.json()["status"] == "SUCCEEDED"


async def test_kpi_summary_matches_approved_baseline() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        all_response = await client.get("/api/v1/readiness/summary")
        rrad_response = await client.get("/api/v1/readiness/summary", params={"depot": "RRAD"})

    assert all_response.status_code == 200
    summary = all_response.json()
    assert summary["command"] == {
        "composite_readiness": 53.6,
        "assets_elevated": 179,
        "workforce_gap": 716,
        "critical_supply": 170,
        "plan_attainment": 88.3,
        "open_ncr": 133,
        "bottlenecks": 13,
    }
    assert summary["assets"] == {
        "count": 1600,
        "average_health": 70.7,
        "high_risk": 10,
        "legacy_analog": 426,
    }
    assert summary["supply"]["scope"] == "GLOBAL"
    assert summary["assessment"] == {
        "green": 64,
        "yellow": 252,
        "red": 84,
        "ruleset": "prototype-v1",
    }
    assert [driver["name"] for driver in summary["drivers"]] == [
        "Workforce Capacity",
        "Supply Chain",
        "Asset Availability",
        "Production Flow",
        "Quality/Rework",
    ]
    assert summary["drivers"][0]["value"] == 100.0
    assert rrad_response.json()["command"]["composite_readiness"] == 51.3
    assert rrad_response.json()["supply"] == summary["supply"]


async def test_invalid_filters_and_pagination_are_rejected() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        unknown_depot = await client.get("/api/v1/assets", params={"depot": "UNKNOWN"})
        invalid_size = await client.get("/api/v1/assets", params={"size": 101})
        invalid_grade = await client.get(
            "/api/v1/connectivity-assessments", params={"grade": "Blue"}
        )

    assert unknown_depot.status_code == 404
    assert invalid_size.status_code == 422
    assert invalid_grade.status_code == 422
