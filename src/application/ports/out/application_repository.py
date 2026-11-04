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
    async def get_all(self) -> list[Application]:
        """List all applications."""

    @abstractmethod
    async def update_status(self, application_id: int, status: str) -> Application | None:
        """Update application status."""