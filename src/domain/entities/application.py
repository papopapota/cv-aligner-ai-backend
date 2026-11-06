from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Application:
    """Pure domain entity representing a job application.

    It has no persistence dependencies: the SQLAlchemy mapping lives in the
    infrastructure layer (``ApplicationModel``).
    """

    id: int | None
    user_id: int
    job_title: str
    company: str
    status: str
    created_at: datetime
