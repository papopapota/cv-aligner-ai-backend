from __future__ import annotations

from pydantic import BaseModel, Field

from src.domain.job_url_rules import MAX_JOB_URL_LENGTH


class JobDescriptionExtractRequest(BaseModel):
    url: str = Field(
        ...,
        min_length=1,
        max_length=MAX_JOB_URL_LENGTH,
        description="URL pública de la oferta de trabajo.",
    )


class JobDescriptionExtractResponse(BaseModel):
    title: str | None = None
    company: str | None = None
    description: str
