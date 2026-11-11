from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.ports.inbound.cv_query_use_case import CVQueryUseCase
from src.application.ports.out.cv_repository_port import CVRepositoryPort
from src.application.services.cv_query_service import CVQueryService
from src.domain.cv_status import CVStatus
from src.domain.entities.cv import CV
from src.domain.errors import CVNotFoundError

_USER_ID = 7


def _cv(**overrides: object) -> CV:
    values: dict[str, object] = {
        "id": uuid4(),
        "user_id": _USER_ID,
        "s3_key": "users/7/cvs/cv.pdf",
        "filename": "cv.pdf",
        "content_type": "application/pdf",
        "size_bytes": 1024,
        "sha256": "a" * 64,
        "status": CVStatus.UPLOADED,
    }
    values.update(overrides)
    return CV(**values)  # type: ignore[arg-type]


@pytest.fixture
def repository() -> AsyncMock:
    return AsyncMock(spec=CVRepositoryPort)


@pytest.fixture
def service(repository: AsyncMock) -> CVQueryService:
    return CVQueryService(repository)


async def test_returns_a_cv_owned_by_the_user(
    service: CVQueryService,
    repository: AsyncMock,
) -> None:
    cv = _cv()
    repository.get_by_id.return_value = cv

    result = await service.get(cv.id, _USER_ID)

    assert result is cv
    repository.get_by_id.assert_awaited_once_with(cv.id, _USER_ID)


async def test_raises_when_the_cv_does_not_exist(
    service: CVQueryService,
    repository: AsyncMock,
) -> None:
    repository.get_by_id.return_value = None
    cv_id = uuid4()

    with pytest.raises(CVNotFoundError, match=str(cv_id)):
        await service.get(cv_id, _USER_ID)


async def test_lists_only_the_users_cvs(
    service: CVQueryService,
    repository: AsyncMock,
) -> None:
    cvs = [_cv(), _cv()]
    repository.list_by_user.return_value = cvs

    result = await service.list(_USER_ID)

    assert result == cvs
    repository.list_by_user.assert_awaited_once_with(_USER_ID)


async def test_satisfies_the_inbound_port(service: CVQueryService) -> None:
    assert isinstance(service, CVQueryUseCase)
