import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
def client() -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )

async def test_health_check_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_the_openapi_exposes_every_route() -> None:
    paths = app.openapi()["paths"]

    assert sorted(paths) == [
        "/api/v1/applications",
        "/api/v1/applications/{application_id}",
        "/api/v1/applications/{application_id}/status",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/register",
        "/api/v1/cvs",
        "/api/v1/cvs/{cv_id}",
        "/api/v1/cvs/{cv_id}/content",
        "/api/v1/cvs/{cv_id}/optimize",
        "/health",
    ]

async def test_legacy_unversioned_routes_are_removed(client: AsyncClient) -> None:
    assert (await client.get("/applications")).status_code == 404
    assert (await client.post("/auth/login", json={})).status_code == 404
    assert (await client.post("/cv/upload")).status_code == 404


def test_the_cv_upload_route_is_declared_as_multipart() -> None:
    operation = app.openapi()["paths"]["/api/v1/cvs"]["post"]

    content_types = operation["requestBody"]["content"].keys()

    assert "multipart/form-data" in content_types


def test_the_cv_optimize_route_accepts_json() -> None:
    operation = app.openapi()["paths"]["/api/v1/cvs/{cv_id}/optimize"]["post"]

    content_types = operation["requestBody"]["content"].keys()

    assert "application/json" in content_types
