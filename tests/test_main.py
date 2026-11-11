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
        "/api/v1/cvs",
        "/api/v1/cvs/{cv_id}",
        "/api/v1/cvs/{cv_id}/optimize",
        "/applications",
        "/applications/{application_id}",
        "/applications/{application_id}/status",
        "/auth/login",
        "/auth/refresh",
        "/auth/register",
        "/health",
    ]

def test_the_cv_upload_route_is_declared_as_multipart() -> None:
    operation = app.openapi()["paths"]["/api/v1/cvs"]["post"]

    content_types = operation["requestBody"]["content"].keys()

    assert "multipart/form-data" in content_types


def test_the_cv_optimize_route_accepts_json() -> None:
    operation = app.openapi()["paths"]["/api/v1/cvs/{cv_id}/optimize"]["post"]

    content_types = operation["requestBody"]["content"].keys()

    assert "application/json" in content_types
