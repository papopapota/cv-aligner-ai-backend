from unittest.mock import AsyncMock

import pytest

from src.application.ports.out.job_description_source_port import JobDescriptionSourcePort
from src.application.services.extract_job_description_service import (
    ExtractJobDescriptionService,
)
from src.domain.errors import EmptyContentError, InvalidJobUrlError
from src.domain.job_posting_content import JobPostingContent

_URL = "https://example.com/ofertas/123"


async def test_returns_the_content_from_the_source() -> None:
    source = AsyncMock(spec=JobDescriptionSourcePort)
    source.fetch_content.return_value = JobPostingContent(
        title="  Backend Engineer  ",
        company="  Acme Corp ",
        description="  Buscamos Python y FastAPI.  ",
    )
    service = ExtractJobDescriptionService(source)

    content = await service.execute(_URL)

    assert content == JobPostingContent(
        title="Backend Engineer",
        company="Acme Corp",
        description="Buscamos Python y FastAPI.",
    )
    source.fetch_content.assert_awaited_once_with(_URL)


async def test_normalizes_empty_metadata_to_none() -> None:
    source = AsyncMock(spec=JobDescriptionSourcePort)
    source.fetch_content.return_value = JobPostingContent(
        title="   ",
        company="",
        description="Buscamos Python.",
    )
    service = ExtractJobDescriptionService(source)

    content = await service.execute(_URL)

    assert content.title is None
    assert content.company is None


async def test_validates_the_url_before_calling_the_source() -> None:
    source = AsyncMock(spec=JobDescriptionSourcePort)
    service = ExtractJobDescriptionService(source)

    with pytest.raises(InvalidJobUrlError):
        await service.execute("http://127.0.0.1/admin")

    source.fetch_content.assert_not_awaited()


async def test_rejects_an_empty_description() -> None:
    source = AsyncMock(spec=JobDescriptionSourcePort)
    source.fetch_content.return_value = JobPostingContent(
        title=None, company=None, description="   \n  "
    )
    service = ExtractJobDescriptionService(source)

    with pytest.raises(EmptyContentError):
        await service.execute(_URL)
