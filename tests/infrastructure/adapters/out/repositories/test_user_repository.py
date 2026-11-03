from collections.abc import AsyncIterator
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from src.domain.entities.user import User
from src.domain.errors import UserAlreadyExistsError
from src.infrastructure.adapters.out.repositories.models import UserModel  # noqa: F401
from src.infrastructure.adapters.out.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from src.infrastructure.database import Base


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session

    await engine.dispose()


@pytest.fixture
def repository(session: AsyncSession) -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(session)


async def test_create_persists_the_user(repository: SQLAlchemyUserRepository) -> None:
    user = await repository.create(
        name="Juan Perez",
        email="juan@example.com",
        password="hashed-password",
    )

    assert user.id == 1
    assert user.name == "Juan Perez"
    assert user.email == "juan@example.com"
    assert user.password == "hashed-password"
    assert isinstance(user.created_at, datetime)


async def test_get_by_email_returns_the_user(
    repository: SQLAlchemyUserRepository,
) -> None:
    await repository.create(
        name="Juan Perez",
        email="juan@example.com",
        password="hashed-password",
    )

    user = await repository.get_by_email("juan@example.com")

    assert user is not None
    assert user.email == "juan@example.com"


async def test_get_by_email_returns_none_when_missing(
    repository: SQLAlchemyUserRepository,
) -> None:
    user = await repository.get_by_email("missing@example.com")

    assert user is None


async def test_get_by_id_returns_the_user(
    repository: SQLAlchemyUserRepository,
) -> None:
    created = await repository.create(
        name="Juan Perez",
        email="juan@example.com",
        password="hashed-password",
    )

    user = await repository.get_by_id(created.id)

    assert user is not None
    assert user.id == created.id


async def test_create_raises_when_email_is_already_registered(
    repository: SQLAlchemyUserRepository,
) -> None:
    await repository.create(
        name="Juan Perez",
        email="juan@example.com",
        password="hashed-password",
    )

    with pytest.raises(UserAlreadyExistsError):
        await repository.create(
            name="Other Name",
            email="juan@example.com",
            password="other-password",
        )


async def test_update_persists_the_changes(
    repository: SQLAlchemyUserRepository,
) -> None:
    created = await repository.create(
        name="Juan Perez",
        email="juan@example.com",
        password="hashed-password",
    )
    updated = User(
        id=created.id,
        name="Juan Actualizado",
        email="nuevo@example.com",
        password="new-hash",
        created_at=created.created_at,
    )

    result = await repository.update(updated)
    persisted = await repository.get_by_id(created.id)

    assert result.name == "Juan Actualizado"
    assert persisted is not None
    assert persisted.email == "nuevo@example.com"
    assert persisted.password == "new-hash"


async def test_delete_removes_the_user(
    repository: SQLAlchemyUserRepository,
) -> None:
    created = await repository.create(
        name="Juan Perez",
        email="juan@example.com",
        password="hashed-password",
    )

    await repository.delete(created.id)

    assert await repository.get_by_id(created.id) is None
