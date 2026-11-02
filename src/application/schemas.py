from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ApplicationCreate(BaseModel):
    """Schema to create a new application.
    
    Requires user_id to associate the application with a registered user.
    """
    job_title: str = Field(..., description="Título del puesto")
    company: str = Field(..., description="Nombre de la empresa")
    user_id: int = Field(..., description="ID del usuario registrado")

    model_config = {"from_attributes": True}


class ApplicationResponse(BaseModel):
    """Schema for application response."""
    id: int
    user_id: int
    job_title: str
    company: str
    status: str
    created_at: datetime

    @classmethod
    def from_domain(cls, application: "Application") -> "ApplicationResponse":
        """Convert from domain entity to schema."""
        return cls(
            id=application.id if application.id is not None else 0,
            user_id=application.user_id,
            job_title=application.job_title,
            company=application.company,
            status=application.status,
            created_at=application.created_at,
        )