from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from src.application.ports.out.application_repository import ApplicationRepositoryPort
from src.application.schemas import ApplicationCreate
from src.application.use_cases import ApplicationUseCase
from src.domain.entities.application import Application


def _application(
    application_id: int = 1,
    user_id: int = 7,
    status: str = "pending",
) -> Application:
    return Application(
        id=application_id,
        user_id=user_id,
        job_title="Desarrollador Frontend",
        company="Tech Corp",
        status=status,
        created_at=datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc),
    )


@pytest.fixture
def repository() -> AsyncMock:
    return AsyncMock(spec=ApplicationRepositoryPort)


@pytest.fixture
def use_case(repository: AsyncMock) -> ApplicationUseCase:
    return ApplicationUseCase(repository)


async def test_create_application_forces_the_owner_and_pending_status(
    use_case: ApplicationUseCase,
    repository: AsyncMock,
) -> None:
    repository.create.return_value = _application()

    response = await use_case.create_application(
        user_id=7,
        data=ApplicationCreate(job_title="Desarrollador Frontend", company="Tech Corp"),
    )

    created = repository.create.await_args.args[0]
    assert created.user_id == 7
    assert created.status == "pending"
    assert response.user_id == 7


async def test_list_applications_maps_the_repository_results(
    use_case: ApplicationUseCase,
    repository: AsyncMock,
) -> None:
    repository.list_by_user.return_value = [_application(), _application(2)]

    responses = await use_case.list_applications(user_id=7)

    assert [response.id for response in responses] == [1, 2]
    repository.list_by_user.assert_awaited_once_with(7)


async def test_update_status_returns_none_when_the_application_does_not_exist(
    use_case: ApplicationUseCase,
    repository: AsyncMock,
) -> None:
    repository.update_status.return_value = None

    response = await use_case.update_application_status(99, 7, "accepted")

    assert response is None
    repository.update_status.assert_awaited_once_with(99, 7, "accepted")


async def test_delete_application_returns_the_repository_result(
    use_case: ApplicationUseCase,
    repository: AsyncMock,
) -> None:
    repository.delete.return_value = True

    deleted = await use_case.delete_application(1, 7)

    assert deleted is True
    repository.delete.assert_awaited_once_with(1, 7)
