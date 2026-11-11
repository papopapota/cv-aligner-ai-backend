from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.cv_status import CVStatus
from src.domain.entities.cv import CV
from src.domain.structured_cv import StructuredCV


class CVRepositoryPort(ABC):
    """Persistence port for stored CVs."""

    @abstractmethod
    async def create(self, cv: CV) -> CV:
        """Persist a new CV."""

    @abstractmethod
    async def get_by_id(self, cv_id: UUID, user_id: int) -> CV | None:
        """Return the CV when it exists and belongs to ``user_id``."""

    @abstractmethod
    async def get_by_id_unscoped(self, cv_id: UUID) -> CV | None:
        """Return the CV regardless of its owner.

        Used by background processing where the user identity is not available.
        """

    @abstractmethod
    async def get_status_by_id(self, cv_id: UUID, user_id: int) -> CV | None:
        """Return the CV metadata without loading its content."""

    @abstractmethod
    async def list_status_by_user(self, user_id: int) -> list[CV]:
        """List the CV metadata owned by a user without loading content."""

    @abstractmethod
    async def update_status(self, cv_id: UUID, status: CVStatus) -> CV | None:
        """Update the lifecycle status of a CV."""

    @abstractmethod
    async def save_parsed(
        self,
        cv_id: UUID,
        raw_text: str,
        structured_cv: StructuredCV,
    ) -> CV | None:
        """Persist the extracted text and structured CV and mark it as parsed."""

    @abstractmethod
    async def mark_error(
        self,
        cv_id: UUID,
        error_code: str,
        error_message: str,
    ) -> CV | None:
        """Mark a CV as failed while keeping its stored data and S3 key."""

    @abstractmethod
    async def list_by_user(self, user_id: int) -> list[CV]:
        """List the CVs owned by a user, newest first."""
