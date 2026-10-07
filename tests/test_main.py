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

    assert sorted(paths) == ["/cv/optimize", "/cv/upload", "/health"]


def test_the_optimize_route_is_declared_as_multipart() -> None:
    operation = app.openapi()["paths"]["/cv/optimize"]["post"]

    content_types = operation["requestBody"]["content"].keys()

    assert "multipart/form-data" in content_types
