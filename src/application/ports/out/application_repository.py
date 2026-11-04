from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities.application import Application


class ApplicationRepositoryPort(ABC):
    """Port abstract for Application repository."""

    @abstractmethod
    async def create(self, application: Application) -> Application:
        """Create a new application."""

    @abstractmethod
    async def get_by_id(self, application_id: int) -> Application | None:
        """Get application by ID."""

    @abstractmethod
    async def list_by_user(self, user_id: int) -> list[Application]:
        """List the applications owned by a user."""

    @abstractmethod
    async def update_status(
        self,
        application_id: int,
        user_id: int,
        status: str,
    ) -> Application | None:
        """Update the status of an application owned by a user."""

    @abstractmethod
    async def delete(self, application_id: int, user_id: int) -> bool:
        """Delete an application owned by a user.

        Returns ``True`` when the application existed and was deleted.
        """
