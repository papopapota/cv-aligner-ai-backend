from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from src.application.ports.out.cv_repository_port import CVRepositoryPort
from src.domain.cv_status import CVStatus
from src.domain.entities.cv import CV
from src.domain.structured_cv import StructuredCV
from src.infrastructure.adapters.out.repositories.models import CVModel

_STATUS_COLUMNS = (
    CVModel.id,
    CVModel.user_id,
    CVModel.s3_key,
    CVModel.filename,
    CVModel.content_type,
    CVModel.size_bytes,
    CVModel.sha256,
    CVModel.status,
    CVModel.error_code,
    CVModel.error_message,
    CVModel.created_at,
    CVModel.updated_at,
)


class SQLAlchemyCVRepository(CVRepositoryPort):
    """Implementation of CVRepositoryPort using SQLAlchemy 2.0 async sessions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(model: CVModel) -> CV:
        structured_cv = (
            StructuredCV.from_mapping(model.structured_json)
            if model.structured_json is not None
            else None
        )
        return CV(
            id=model.id,
            user_id=model.user_id,
            s3_key=model.s3_key,
            filename=model.filename,
            content_type=model.content_type,
            size_bytes=model.size_bytes,
            sha256=model.sha256,
            status=CVStatus(model.status),
            raw_text=model.raw_text,
            structured_cv=structured_cv,
            error_code=model.error_code,
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_status_domain(model: CVModel) -> CV:
        return CV(
            id=model.id,
            user_id=model.user_id,
            s3_key=model.s3_key,
            filename=model.filename,
            content_type=model.content_type,
            size_bytes=model.size_bytes,
            sha256=model.sha256,
            status=CVStatus(model.status),
            raw_text=None,
            structured_cv=None,
            error_code=model.error_code,
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def create(self, cv: CV) -> CV:
        model = CVModel(
            id=cv.id,
            user_id=cv.user_id,
            s3_key=cv.s3_key,
            filename=cv.filename,
            content_type=cv.content_type,
            size_bytes=cv.size_bytes,
            sha256=cv.sha256,
            status=cv.status.value,
            raw_text=cv.raw_text,
            structured_json=(
                cv.structured_cv.to_dict() if cv.structured_cv is not None else None
            ),
            error_code=cv.error_code,
            error_message=cv.error_message,
        )
        self._session.add(model)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise
        await self._session.refresh(model)
        return self._to_domain(model)

    async def get_by_id(self, cv_id: UUID, user_id: int) -> CV | None:
        result = await self._session.execute(
            select(CVModel).where(
                CVModel.id == cv_id,
                CVModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def get_by_id_unscoped(self, cv_id: UUID) -> CV | None:
        model = await self._session.get(CVModel, cv_id)
        if model is None:
            return None
        return self._to_domain(model)

    async def get_status_by_id(self, cv_id: UUID, user_id: int) -> CV | None:
        result = await self._session.execute(
            select(CVModel)
            .options(load_only(*_STATUS_COLUMNS))
            .where(
                CVModel.id == cv_id,
                CVModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_status_domain(model)

    async def list_status_by_user(self, user_id: int) -> list[CV]:
        result = await self._session.execute(
            select(CVModel)
            .options(load_only(*_STATUS_COLUMNS))
            .where(CVModel.user_id == user_id)
            .order_by(CVModel.created_at.desc())
        )
        return [self._to_status_domain(model) for model in result.scalars().all()]

    async def update_status(self, cv_id: UUID, status: CVStatus) -> CV | None:
        if status is CVStatus.ERROR:
            raise ValueError("Use mark_error to move a CV to ERROR status.")
        model = await self._session.get(CVModel, cv_id)
        if model is None:
            return None
        model.status = status.value
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def save_parsed(
        self,
        cv_id: UUID,
        raw_text: str,
        structured_cv: StructuredCV,
    ) -> CV | None:
        model = await self._session.get(CVModel, cv_id)
        if model is None:
            return None
        model.raw_text = raw_text
        model.structured_json = structured_cv.to_dict()
        model.status = CVStatus.PARSED.value
        model.error_code = None
        model.error_message = None
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def mark_error(
        self,
        cv_id: UUID,
        error_code: str,
        error_message: str,
    ) -> CV | None:
        model = await self._session.get(CVModel, cv_id)
        if model is None:
            return None
        model.status = CVStatus.ERROR.value
        model.error_code = error_code
        model.error_message = error_message
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def list_by_user(self, user_id: int) -> list[CV]:
        result = await self._session.execute(
            select(CVModel)
            .where(CVModel.user_id == user_id)
            .order_by(CVModel.created_at.desc())
        )
        return [self._to_domain(model) for model in result.scalars().all()]
