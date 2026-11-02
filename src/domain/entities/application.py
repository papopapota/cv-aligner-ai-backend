from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database import Base


class Application(Base):
    """Domain entity representing a job application.
    
    Maps to the existing 'applications' table which is already defined
    in the codebase. Uses extend_existing to avoid table redefinition.
    Uses job_title and company fields, with status defaulting to 'pending'.
    The user_id field has a ForeignKey constraint to the users table.
    """
    __tablename__ = "applications"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    job_title: Mapped[str] = mapped_column(String(255))
    company: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="pending", server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default="CURRENT_TIMESTAMP")

    def __init__(
        self, 
        user_id: int, 
        job_title: str, 
        company: str, 
        status: str = "pending", 
        created_at: datetime | None = None
    ) -> None:
        self.user_id = user_id
        self.job_title = job_title
        self.company = company
        self.status = status
        self.created_at = created_at or datetime.utcnow()

    def __repr__(self) -> str:
        return f"Application(id={self.id}, user_id={self.user_id}, job_title={self.job_title!r}, company={self.company!r}, status={self.status!r})"