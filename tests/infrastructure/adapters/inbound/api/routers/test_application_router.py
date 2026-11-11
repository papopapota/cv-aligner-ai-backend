from collections.abc import AsyncIterator
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.ports.out.application_repository import ApplicationRepositoryPort
from src.application.ports.out.user_port import UserRepositoryPort
from src.domain.entities.application import Application
from src.domain.entities.user import User
from src.infrastructure.adapters.inbound.api.routers.application_router import (
    get_application_repository,
)
from src.infrastructure.adapters.inbound.api.routers.auth_router import (
    get_user_repository,
)
from src.infrastructure.security import create_access_token
from src.main import app


def _user() -> User:
    return User(
        id=7,
        name="Juan Perez",
        email="juan@example.com",
        password="hashed-password",
        created_at=datetime.now(timezone.utc),
    )


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
def user_repository() -> AsyncMock:
    return AsyncMock(spec=UserRepositoryPort)


@pytest.fixture
def application_repository() -> AsyncMock:
    return AsyncMock(spec=ApplicationRepositoryPort)


@pytest.fixture
async def client(
    user_repository: AsyncMock,
    application_repository: AsyncMock,
) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_user_repository] = lambda: user_repository
    app.dependency_overrides[get_application_repository] = lambda: (
        application_repository
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


def _auth_headers() -> dict[str, str]:
    token = create_access_token(subject="juan@example.com")
    return {"Authorization": f"Bearer {token}"}


async def test_list_applications_requires_authentication(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/applications")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


async def test_list_applications_rejects_an_invalid_token(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/applications",
        headers={"Authorization": "Bearer not-a-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


async def test_list_applications_returns_only_the_current_users_applications(
    client: AsyncClient,
    user_repository: AsyncMock,
    application_repository: AsyncMock,
) -> None:
    user_repository.get_by_email.return_value = _user()
    application_repository.list_by_user.return_value = [_application()]

    response = await client.get("/api/v1/applications", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "user_id": 7,
            "job_title": "Desarrollador Frontend",
            "company": "Tech Corp",
            "status": "pending",
            "created_at": "2026-01-15T10:30:00Z",
        }
    ]
    application_repository.list_by_user.assert_awaited_once_with(7)


async def test_create_application_uses_the_authenticated_user(
    client: AsyncClient,
    user_repository: AsyncMock,
    application_repository: AsyncMock,
) -> None:
    user_repository.get_by_email.return_value = _user()
    application_repository.create.return_value = _application()

    response = await client.post(
        "/api/v1/applications",
        headers=_auth_headers(),
        json={"job_title": "Desarrollador Frontend", "company": "Tech Corp"},
    )

    assert response.status_code == 201
    created = application_repository.create.await_args.args[0]
    assert created.user_id == 7
    assert created.job_title == "Desarrollador Frontend"


async def test_update_status_uses_the_body_and_returns_the_application(
    client: AsyncClient,
    user_repository: AsyncMock,
    application_repository: AsyncMock,
) -> None:
    user_repository.get_by_email.return_value = _user()
    application_repository.update_status.return_value = _application(status="accepted")

    response = await client.patch(
        "/api/v1/applications/1/status",
        headers=_auth_headers(),
        json={"status": "accepted"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    application_repository.update_status.assert_awaited_once_with(1, 7, "accepted")


async def test_update_status_returns_404_for_an_application_of_another_user(
    client: AsyncClient,
    user_repository: AsyncMock,
    application_repository: AsyncMock,
) -> None:
    user_repository.get_by_email.return_value = _user()
    application_repository.update_status.return_value = None

    response = await client.patch(
        "/api/v1/applications/99/status",
        headers=_auth_headers(),
        json={"status": "accepted"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found"}


async def test_update_status_rejects_an_unknown_status(
    client: AsyncClient,
    user_repository: AsyncMock,
) -> None:
    user_repository.get_by_email.return_value = _user()

    response = await client.patch(
        "/api/v1/applications/1/status",
        headers=_auth_headers(),
        json={"status": "invented"},
    )

    assert response.status_code == 422


async def test_delete_application_uses_the_authenticated_user(
    client: AsyncClient,
    user_repository: AsyncMock,
    application_repository: AsyncMock,
) -> None:
    user_repository.get_by_email.return_value = _user()
    application_repository.delete.return_value = True

    response = await client.delete("/api/v1/applications/1", headers=_auth_headers())

    assert response.status_code == 204
    assert response.content == b""
    application_repository.delete.assert_awaited_once_with(1, 7)


async def test_delete_application_returns_404_for_an_application_of_another_user(
    client: AsyncClient,
    user_repository: AsyncMock,
    application_repository: AsyncMock,
) -> None:
    user_repository.get_by_email.return_value = _user()
    application_repository.delete.return_value = False

    response = await client.delete("/api/v1/applications/99", headers=_auth_headers())

    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found"}
