from __future__ import annotations

from datetime import datetime

from src.application.schemas import ApplicationCreate, ApplicationResponse
from src.infrastructure.adapters.out.repositories.models import ApplicationModel
from sqlalchemy import select
from src.infrastructure.database import async_session_factory


class ApplicationUseCase:
    """Case of use for Application management."""

    def __init__(self) -> None:
        pass

    async def create_application(self, data: ApplicationCreate) -> ApplicationResponse:
        """Create a new application.
        
        Requires user_id to be provided in the data to associate with a registered user.
        """
        async with async_session_factory() as session:
            application = ApplicationModel(
                user_id=data.user_id,
                job_title=data.job_title,
                company=data.company,
                status="pending",
            )
            session.add(application)
            await session.flush()
            await session.commit()  # Add commit
            await session.refresh(application)
            return ApplicationResponse(
                id=application.id,
                user_id=application.user_id,
                job_title=application.job_title,
                company=application.company,
                status=application.status,
                created_at=application.created_at,
            )

    async def list_applications(self, user_id: int) -> list[ApplicationResponse]:
        """List applications for a specific user.
        
        Filters applications by user_id.
        """
        async with async_session_factory() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(ApplicationModel).where(ApplicationModel.user_id == user_id)
            )
            applications = result.scalars().all()
            return [
                ApplicationResponse(
                    id=app.id,
                    user_id=app.user_id,
                    job_title=app.job_title,
                    company=app.company,
                    status=app.status,
                    created_at=app.created_at,
                )
                for app in applications
            ]

    async def update_application_status(
        self, application_id: int, status: str
    ) -> ApplicationResponse | None:
        """Update application status."""
        async with async_session_factory() as session:
            application = await session.get(ApplicationModel, application_id)
            if application is None:
                return None
            application.status = status
            await session.flush()
            await session.commit()  # Add commit
            await session.refresh(application)
            return ApplicationResponse(
                id=application.id,
                user_id=application.user_id,
                job_title=application.job_title,
                company=application.company,
                status=application.status,
                created_at=application.created_at,
            )