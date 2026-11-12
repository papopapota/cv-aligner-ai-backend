from collections.abc import AsyncIterator
from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from src.domain.cv_sections import CVSections
from src.domain.cv_status import CVStatus
from src.domain.entities.cv import CV
from src.domain.personal_info import PersonalInfo
from src.domain.semantic_profile import SemanticProfile
from src.domain.structured_cv import StructuredCV
from src.infrastructure.adapters.out.repositories.cv_repository import (
    SQLAlchemyCVRepository,
)
from src.infrastructure.adapters.out.repositories.models import CVModel, UserModel
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
def repository(session: AsyncSession) -> SQLAlchemyCVRepository:
    return SQLAlchemyCVRepository(session)


async def _create_user(session: AsyncSession, email: str = "ana@example.com") -> UserModel:
    user = UserModel(name="Ana Developer", email=email, password="hashed-password")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def _cv(user_id: int, **overrides: object) -> CV:
    values: dict[str, object] = {
        "id": uuid4(),
        "user_id": user_id,
        "s3_key": f"users/{user_id}/cv-{uuid4()}.pdf",
        "filename": "cv.pdf",
        "content_type": "application/pdf",
        "size_bytes": 1024,
        "sha256": "a" * 64,
        "status": CVStatus.UPLOADED,
    }
    values.update(overrides)
    return CV(**values)  # type: ignore[arg-type]


def _structured_cv() -> StructuredCV:
    return StructuredCV(
        personal_info=PersonalInfo(full_name="Ana Developer"),
        technical_data=SemanticProfile(
            summary="Backend engineer",
            technical_skills="python, fastapi",
            projects="cv-aligner",
        ),
    )


def _sections() -> CVSections:
    return CVSections(
        summary="Backend engineer",
        technical_skills="python, fastapi",
        projects="cv-aligner",
    )


async def test_create_persists_the_cv(
    session: AsyncSession,
    repository: SQLAlchemyCVRepository,
) -> None:
    user = await _create_user(session)
    cv = _cv(user.id)

    created = await repository.create(cv)

    assert created.id == cv.id
    assert created.user_id == user.id
    assert created.s3_key == cv.s3_key
    assert created.filename == "cv.pdf"
    assert created.content_type == "application/pdf"
    assert created.size_bytes == 1024
    assert created.sha256 == "a" * 64
    assert created.status is CVStatus.UPLOADED
    assert created.created_at is not None
    assert created.updated_at is not None


async def test_create_persists_structured_data(
    session: AsyncSession,
    repository: SQLAlchemyCVRepository,
) -> None:
    user = await _create_user(session)
    structured = _structured_cv()

    created = await repository.create(
        _cv(user.id, status=CVStatus.PARSED, structured_cv=structured)
    )

    assert created.structured_cv == structured


async def test_get_by_id_returns_the_owned_cv(
    session: AsyncSession,
    repository: SQLAlchemyCVRepository,
) -> None:
    user = await _create_user(session)
    created = await repository.create(_cv(user.id))

    found = await repository.get_by_id(created.id, user.id)

    assert found == created


async def test_get_by_id_hides_cvs_owned_by_another_user(
    session: AsyncSession,
    repository: SQLAlchemyCVRepository,
) -> None:
    owner = await _create_user(session, "owner@example.com")
    other = await _create_user(session, "other@example.com")
    created = await repository.create(_cv(owner.id))

    assert await repository.get_by_id(created.id, other.id) is None
    assert await repository.get_by_id(created.id, owner.id) == created


async def test_get_by_id_returns_none_when_missing(
    repository: SQLAlchemyCVRepository,
) -> None:
    assert await repository.get_by_id(uuid4(), 1) is None


async def test_get_by_id_unscoped_returns_any_cv(
    session: AsyncSession,
    repository: SQLAlchemyCVRepository,
) -> None:
    user = await _create_user(session)
    created = await repository.create(_cv(user.id))

    assert await repository.get_by_id_unscoped(created.id) == created
    assert await repository.get_by_id_unscoped(uuid4()) is None


async def test_get_status_by_id_omits_the_content(
    session: AsyncSession,
    repository: SQLAlchemyCVRepository,
) -> None:
    user = await _create_user(session)
    created = await repository.create(
        _cv(
            user.id,
            status=CVStatus.PARSED,
            raw_text="Ana Developer",
            structured_cv=_structured_cv(),
        )
    )

    found = await repository.get_status_by_id(created.id, user.id)

    assert found is not None
    assert found.id == created.id
    assert found.status is CVStatus.PARSED
    assert found.raw_text is None
    assert found.structured_cv is None
    assert found.parsed_sections == _sections()


async def test_get_status_by_id_hides_cvs_owned_by_another_user(
    session: AsyncSession,
    repository: SQLAlchemyCVRepository,
) -> None:
    owner = await _create_user(session, "owner@example.com")
    other = await _create_user(session, "other@example.com")
    created = await repository.create(_cv(owner.id))

    assert await repository.get_status_by_id(created.id, other.id) is None
    assert await repository.get_status_by_id(created.id, owner.id) is not None


async def test_get_status_by_id_returns_none_when_missing(
    repository: SQLAlchemyCVRepository,
) -> None:
    assert await repository.get_status_by_id(uuid4(), 1) is None


async def test_list_status_by_user_omits_the_content(
    session: AsyncSession,
    repository: SQLAlchemyCVRepository,
) -> None:
    owner = await _create_user(session, "owner@example.com")
    other = await _create_user(session, "other@example.com")
    first = await repository.create(_cv(owner.id))
    second = await repository.create(
        _cv(
            owner.id,
            status=CVStatus.PARSED,
            raw_text="Ana Developer",
            structured_cv=_structured_cv(),
        )
    )
    await repository.create(_cv(other.id))

    await session.execute(
        update(CVModel)
        .where(CVModel.id == first.id)
        .values(created_at=datetime(2020, 1, 1))
    )
    await session.execute(
        update(CVModel)
        .where(CVModel.id == second.id)
        .values(created_at=datetime(2021, 1, 1))
    )
    await session.commit()

    listed = await repository.list_status_by_user(owner.id)

    assert [cv.id for cv in listed] == [second.id, first.id]
    assert all(cv.raw_text is None for cv in listed)
    assert all(cv.structured_cv is None for cv in listed)
    assert all(cv.parsed_sections is None for cv in listed)


async def test_update_status_changes_the_lifecycle_state(
    session: AsyncSession,
    repository: SQLAlchemyCVRepository,
) -> None:
    user = await _create_user(session)
    created = await repository.create(_cv(user.id))

    updated = await repository.update_status(created.id, CVStatus.PARSING)

    assert updated is not None
    assert updated.status is CVStatus.PARSING


async def test_update_status_rejects_the_error_state(
    session: AsyncSession,
    repository: SQLAlchemyCVRepository,
) -> None:
    user = await _create_user(session)
    created = await repository.create(_cv(user.id))

    with pytest.raises(ValueError):
        await repository.update_status(created.id, CVStatus.ERROR)


async def test_update_status_returns_none_when_missing(
    repository: SQLAlchemyCVRepository,
) -> None:
    assert await repository.update_status(uuid4(), CVStatus.PARSING) is None


async def test_save_parsed_persists_text_and_structure(
    session: AsyncSession,
    repository: SQLAlchemyCVRepository,
) -> None:
    user = await _create_user(session)
    created = await repository.create(_cv(user.id))
    structured = _structured_cv()

    updated = await repository.save_parsed(
        created.id,
        raw_text="Ana Developer\nBackend engineer",
        structured_cv=structured,
    )

    assert updated is not None
    assert updated.status is CVStatus.PARSED
    assert updated.raw_text == "Ana Developer\nBackend engineer"
    assert updated.structured_cv == structured
    assert updated.parsed_sections == _sections()
    assert updated.error_code is None
    assert updated.error_message is None


async def test_save_parsed_clears_a_previous_error(
    session: AsyncSession,
    repository: SQLAlchemyCVRepository,
) -> None:
    user = await _create_user(session)
    created = await repository.create(_cv(user.id))
    await repository.mark_error(created.id, "PARSE_FAILED", "Could not parse")

    updated = await repository.save_parsed(
        created.id,
        raw_text="Ana Developer",
        structured_cv=_structured_cv(),
    )

    assert updated is not None
    assert updated.status is CVStatus.PARSED
    assert updated.error_code is None
    assert updated.error_message is None


async def test_save_parsed_returns_none_when_missing(
    repository: SQLAlchemyCVRepository,
) -> None:
    assert (
        await repository.save_parsed(uuid4(), "text", _structured_cv()) is None
    )


async def test_mark_error_keeps_the_stored_data_and_s3_key(
    session: AsyncSession,
    repository: SQLAlchemyCVRepository,
) -> None:
    user = await _create_user(session)
    created = await repository.create(_cv(user.id))
    structured = _structured_cv()
    await repository.save_parsed(created.id, "Ana Developer", structured)

    failed = await repository.mark_error(
        created.id,
        "PARSE_FAILED",
        "The CV could not be processed.",
    )

    assert failed is not None
    assert failed.status is CVStatus.ERROR
    assert failed.error_code == "PARSE_FAILED"
    assert failed.error_message == "The CV could not be processed."
    assert failed.s3_key == created.s3_key
    assert failed.raw_text == "Ana Developer"
    assert failed.structured_cv == structured


async def test_mark_error_returns_none_when_missing(
    repository: SQLAlchemyCVRepository,
) -> None:
    assert await repository.mark_error(uuid4(), "PARSE_FAILED", "failed") is None


async def test_list_by_user_returns_only_owned_cvs_newest_first(
    session: AsyncSession,
    repository: SQLAlchemyCVRepository,
) -> None:
    owner = await _create_user(session, "owner@example.com")
    other = await _create_user(session, "other@example.com")
    first = await repository.create(_cv(owner.id, filename="first.pdf"))
    second = await repository.create(_cv(owner.id, filename="second.pdf"))
    await repository.create(_cv(other.id, filename="other.pdf"))

    await session.execute(
        update(CVModel)
        .where(CVModel.id == first.id)
        .values(created_at=datetime(2020, 1, 1))
    )
    await session.execute(
        update(CVModel)
        .where(CVModel.id == second.id)
        .values(created_at=datetime(2021, 1, 1))
    )
    await session.commit()

    listed = await repository.list_by_user(owner.id)

    assert [cv.filename for cv in listed] == ["second.pdf", "first.pdf"]
