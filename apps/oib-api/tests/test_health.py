from httpx import ASGITransport, AsyncClient, Response
from pytest import MonkeyPatch, mark

from app.main import app

pytestmark = mark.anyio


async def get(path: str) -> Response:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.get(path)


async def test_liveness() -> None:
    response = await get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


async def test_readiness_when_database_is_available(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.health.database_is_ready", lambda: True)

    response = await get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_readiness_when_database_is_unavailable(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.health.database_is_ready", lambda: False)

    response = await get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is not ready"}
