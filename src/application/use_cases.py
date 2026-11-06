from __future__ import annotations

from datetime import datetime, timezone

from src.application.ports.out.application_repository import ApplicationRepositoryPort
from src.application.schemas import ApplicationCreate, ApplicationResponse
from src.domain.entities.application import Application

DEFAULT_APPLICATION_STATUS = "pending"


class ApplicationUseCase:
    """Use case for Application management.

    It only depends on the output port, never on infrastructure details.
    """

    def __init__(self, repository: ApplicationRepositoryPort) -> None:
        self._repository = repository

    async def create_application(
        self,
        user_id: int,
        data: ApplicationCreate,
    ) -> ApplicationResponse:
        """Create a new application owned by ``user_id``."""
        application = Application(
            id=None,
            user_id=user_id,
            job_title=data.job_title,
            company=data.company,
            status=DEFAULT_APPLICATION_STATUS,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        created = await self._repository.create(application)
        return ApplicationResponse.from_domain(created)

    async def list_applications(self, user_id: int) -> list[ApplicationResponse]:
        """List the applications owned by ``user_id``."""
        applications = await self._repository.list_by_user(user_id)
        return [ApplicationResponse.from_domain(app) for app in applications]

    async def update_application_status(
        self,
        application_id: int,
        user_id: int,
        status: str,
    ) -> ApplicationResponse | None:
        """Update the status of an application owned by ``user_id``."""
        application = await self._repository.update_status(
            application_id,
            user_id,
            status,
        )
        if application is None:
            return None
        return ApplicationResponse.from_domain(application)

    async def delete_application(self, application_id: int, user_id: int) -> bool:
        """Delete an application owned by ``user_id``.

        Returns ``False`` when the application does not exist or belongs to
        another user.
        """
        return await self._repository.delete(application_id, user_id)
