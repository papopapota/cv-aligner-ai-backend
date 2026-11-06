from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.out.application_repository import ApplicationRepositoryPort
from src.domain.entities.application import Application
from src.infrastructure.adapters.out.repositories.models import ApplicationModel


class SQLAlchemyApplicationRepository(ApplicationRepositoryPort):
    """SQLAlchemy implementation of ApplicationRepositoryPort."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(model: ApplicationModel) -> Application:
        return Application(
            id=model.id,
            user_id=model.user_id,
            job_title=model.job_title,
            company=model.company,
            status=model.status,
            created_at=model.created_at,
        )

    async def create(self, application: Application) -> Application:
        model = ApplicationModel(
            user_id=application.user_id,
            job_title=application.job_title,
            company=application.company,
            status=application.status,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def get_by_id(self, application_id: int) -> Application | None:
        model = await self._session.get(ApplicationModel, application_id)
        if model is None:
            return None
        return self._to_domain(model)

    async def list_by_user(self, user_id: int) -> list[Application]:
        result = await self._session.execute(
            select(ApplicationModel)
            .where(ApplicationModel.user_id == user_id)
            .order_by(ApplicationModel.created_at.desc())
        )
        return [self._to_domain(model) for model in result.scalars().all()]

    async def update_status(
        self,
        application_id: int,
        user_id: int,
        status: str,
    ) -> Application | None:
        result = await self._session.execute(
            select(ApplicationModel).where(
                ApplicationModel.id == application_id,
                ApplicationModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None

        model.status = status
        await self._session.flush()
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def delete(self, application_id: int, user_id: int) -> bool:
        result = await self._session.execute(
            select(ApplicationModel).where(
                ApplicationModel.id == application_id,
                ApplicationModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False

        await self._session.delete(model)
        await self._session.commit()
        return True
