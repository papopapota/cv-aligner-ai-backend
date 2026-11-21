from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.application.ports.inbound.extract_job_description_use_case import (
    ExtractJobDescriptionUseCase,
)
from src.domain.errors import InvalidJobUrlError, JobDescriptionFetchError
from src.domain.job_posting_content import JobPostingContent
from src.infrastructure.adapters.inbound.api.domain_error_handler import (
    handle_invalid_job_url,
    handle_job_description_fetch,
)
from src.infrastructure.adapters.inbound.api.routers.job_description_router import (
    get_extract_job_description_use_case,
    router,
)

_URL = "https://example.com/ofertas/123"
_DESCRIPTION = "Buscamos experiencia en Python y FastAPI."


@pytest.fixture
def use_case() -> AsyncMock:
    return AsyncMock(spec=ExtractJobDescriptionUseCase)


@pytest.fixture
def app(use_case: AsyncMock) -> FastAPI:
    application = FastAPI()
    application.add_exception_handler(InvalidJobUrlError, handle_invalid_job_url)
    application.add_exception_handler(
        JobDescriptionFetchError, handle_job_description_fetch
    )
    application.dependency_overrides[get_extract_job_description_use_case] = (
        lambda: use_case
    )
    application.include_router(router, prefix="/api/v1")
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as async_client:
        yield async_client


async def test_extracts_the_full_job_posting(
    client: AsyncClient, use_case: AsyncMock
) -> None:
    use_case.execute.return_value = JobPostingContent(
        title="Backend Engineer",
        company="Acme Corp",
        description=_DESCRIPTION,
    )

    response = await client.post(
        "/api/v1/job-descriptions/extract", json={"url": _URL}
    )

    assert response.status_code == 200
    assert response.json() == {
        "title": "Backend Engineer",
        "company": "Acme Corp",
        "description": _DESCRIPTION,
    }
    use_case.execute.assert_awaited_once_with(_URL)


async def test_returns_null_metadata_when_it_is_not_on_the_page(
    client: AsyncClient, use_case: AsyncMock
) -> None:
    use_case.execute.return_value = JobPostingContent(
        title=None, company=None, description=_DESCRIPTION
    )

    response = await client.post(
        "/api/v1/job-descriptions/extract", json={"url": _URL}
    )

    assert response.status_code == 200
    assert response.json() == {
        "title": None,
        "company": None,
        "description": _DESCRIPTION,
    }


async def test_rejects_an_invalid_url(client: AsyncClient, use_case: AsyncMock) -> None:
    use_case.execute.side_effect = InvalidJobUrlError("Solo se permiten URLs http.")

    response = await client.post(
        "/api/v1/job-descriptions/extract", json={"url": "ftp://example.com/job"}
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Solo se permiten URLs http."}


async def test_maps_a_fetch_failure_to_502(
    client: AsyncClient, use_case: AsyncMock
) -> None:
    use_case.execute.side_effect = JobDescriptionFetchError("HTTP 503")

    response = await client.post(
        "/api/v1/job-descriptions/extract", json={"url": _URL}
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "No se pudo obtener la descripción desde la URL."
    }


async def test_requires_a_url(client: AsyncClient) -> None:
    response = await client.post("/api/v1/job-descriptions/extract", json={})

    assert response.status_code == 422
