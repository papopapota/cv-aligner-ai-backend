from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.domain.entities.application import Application

ApplicationStatus = Literal["pending", "under-review", "accepted", "rejected"]


class ApplicationCreate(BaseModel):
    """Schema to create a new application.

    The owner is taken from the authenticated user, never from the payload.
    """

    job_title: str = Field(..., description="Título del puesto")
    company: str = Field(..., description="Nombre de la empresa")

    model_config = {"from_attributes": True}


class ApplicationStatusUpdate(BaseModel):
    """Schema to update the status of an application."""

    status: ApplicationStatus = Field(..., description="Nuevo estado de la postulación")


class ApplicationResponse(BaseModel):
    """Schema for application response."""

    id: int
    user_id: int
    job_title: str
    company: str
    status: str
    created_at: datetime

    @classmethod
    def from_domain(cls, application: Application) -> ApplicationResponse:
        """Convert from domain entity to schema."""
        return cls(
            id=application.id if application.id is not None else 0,
            user_id=application.user_id,
            job_title=application.job_title,
            company=application.company,
            status=application.status,
            created_at=application.created_at,
        )
