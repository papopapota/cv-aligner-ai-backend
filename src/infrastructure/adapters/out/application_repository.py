from __future__ import annotations

from abc import ABC

from src.application.ports.out.application_repository import ApplicationRepositoryPort
from src.infrastructure.database import Base, get_session, async_session_factory
from src.domain.entities.application import Application


class SQLAlchemyApplicationRepository(ApplicationRepositoryPort):
    """SQLAlchemy implementation of ApplicationRepositoryPort."""

    async def create(self, application: Application) -> Application:
        """Create a new application."""
        async with async_session_factory() as session:
            session.add(application)
            await session.flush()
            await session.refresh(application)
            return application

    async def get_by_id(self, application_id: int) -> Application | None:
        """Get application by ID."""
        async with async_session_factory() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(Application).where(Application.id == application_id)
            )
            return result.scalar_one_or_none()

    async def get_all(self) -> list[Application]:
        """List all applications."""
        async with async_session_factory() as session:
            from sqlalchemy import select

            result = await session.execute(select(Application))
            return list(result.scalars().all())

    async def update_status(self, application_id: int, status: str) -> Application | None:
        """Update application status."""
        async with async_session_factory() as session:
            application = await session.get(Application, application_id)
            if application is None:
                return None
            application.status = status
            await session.flush()
            await session.refresh(application)
            return application


# Export instance for dependency injection
application_repository = SQLAlchemyApplicationRepository()