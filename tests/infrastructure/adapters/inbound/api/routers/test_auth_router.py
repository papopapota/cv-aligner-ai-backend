from collections.abc import AsyncIterator
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.ports.out.user_port import UserRepositoryPort
from src.domain.entities.user import User
from src.domain.errors import UserAlreadyExistsError
from src.infrastructure.adapters.inbound.api.routers.auth_router import (
    get_user_repository,
)
from src.infrastructure.security import create_access_token, hash_password
from src.main import app


def _user(password: str = "hashed-password") -> User:
    return User(
        id=1,
        name="Juan Perez",
        email="juan@example.com",
        password=password,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def repository() -> AsyncMock:
    return AsyncMock(spec=UserRepositoryPort)


@pytest.fixture
async def client(repository: AsyncMock) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_user_repository] = lambda: repository
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


async def test_register_returns_the_created_user(
    client: AsyncClient,
    repository: AsyncMock,
) -> None:
    repository.create.return_value = _user()

    response = await client.post(
        "/auth/register",
        json={
            "name": "Juan Perez",
            "email": "juan@example.com",
            "password": "securepassword123",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "juan@example.com"
    assert "password" not in response.json()

    create_kwargs = repository.create.await_args.kwargs
    assert create_kwargs["name"] == "Juan Perez"
    assert create_kwargs["email"] == "juan@example.com"
    assert create_kwargs["password"] != "securepassword123"


async def test_register_returns_400_when_email_is_already_registered(
    client: AsyncClient,
    repository: AsyncMock,
) -> None:
    repository.create.side_effect = UserAlreadyExistsError("juan@example.com")

    response = await client.post(
        "/auth/register",
        json={
            "name": "Juan Perez",
            "email": "juan@example.com",
            "password": "securepassword123",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Email already registered"}


async def test_login_returns_tokens_for_valid_credentials(
    client: AsyncClient,
    repository: AsyncMock,
) -> None:
    repository.get_by_email.return_value = _user(hash_password("securepassword123"))

    response = await client.post(
        "/auth/login",
        json={"email": "juan@example.com", "password": "securepassword123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_returns_401_when_user_does_not_exist(
    client: AsyncClient,
    repository: AsyncMock,
) -> None:
    repository.get_by_email.return_value = None

    response = await client.post(
        "/auth/login",
        json={"email": "juan@example.com", "password": "securepassword123"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}


async def test_login_returns_401_when_password_is_wrong(
    client: AsyncClient,
    repository: AsyncMock,
) -> None:
    repository.get_by_email.return_value = _user(hash_password("correct-password"))

    response = await client.post(
        "/auth/login",
        json={"email": "juan@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}


async def test_refresh_returns_new_tokens(
    client: AsyncClient,
    repository: AsyncMock,
) -> None:
    repository.get_by_email.return_value = _user()
    token = create_access_token(subject="juan@example.com")

    response = await client.post("/auth/refresh", params={"token": token})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]


async def test_refresh_returns_401_for_invalid_token(
    client: AsyncClient,
    repository: AsyncMock,
) -> None:
    response = await client.post("/auth/refresh", params={"token": "invalid"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid refresh token"}
