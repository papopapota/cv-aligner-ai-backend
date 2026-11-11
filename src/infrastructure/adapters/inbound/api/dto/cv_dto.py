from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field

from src.domain.cv_status import CVStatus
from src.domain.entities.cv import CV
from src.domain.optimized_cv import OptimizedCV

ACTION_REQUIRED_REUPLOAD_CV = "REUPLOAD_CV"
ACTION_REQUIRED_WAIT_FOR_PARSING = "WAIT_FOR_PARSING"


def action_required_for(status: CVStatus) -> str | None:
    if status is CVStatus.ERROR:
        return ACTION_REQUIRED_REUPLOAD_CV
    if status in (CVStatus.UPLOADED, CVStatus.PARSING):
        return ACTION_REQUIRED_WAIT_FOR_PARSING
    return None


class CVUploadResponse(BaseModel):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    status: str
    action_required: str | None
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_domain(cls, cv: CV) -> CVUploadResponse:
        return cls(
            id=cv.id,
            filename=cv.filename,
            content_type=cv.content_type,
            size_bytes=cv.size_bytes,
            sha256=cv.sha256,
            status=cv.status.value,
            action_required=action_required_for(cv.status),
            created_at=cv.created_at,
            updated_at=cv.updated_at,
        )


class CVStatusResponse(BaseModel):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    status: str
    error_code: str | None
    error_message: str | None
    action_required: str | None
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_domain(cls, cv: CV) -> CVStatusResponse:
        return cls(
            id=cv.id,
            filename=cv.filename,
            content_type=cv.content_type,
            size_bytes=cv.size_bytes,
            sha256=cv.sha256,
            status=cv.status.value,
            error_code=cv.error_code,
            error_message=cv.error_message,
            action_required=action_required_for(cv.status),
            created_at=cv.created_at,
            updated_at=cv.updated_at,
        )


class CVContentResponse(BaseModel):
    id: UUID
    status: str
    raw_text: str
    characters_extracted: int
    structured_cv: dict[str, object] | None = None

    @classmethod
    def from_domain(
        cls,
        cv: CV,
        include_structured: bool = False,
    ) -> CVContentResponse:
        if cv.raw_text is None:
            raise ValueError("The CV content is not available.")
        return cls(
            id=cv.id,
            status=cv.status.value,
            raw_text=cv.raw_text,
            characters_extracted=len(cv.raw_text),
            structured_cv=(
                cv.structured_cv.to_dict()
                if include_structured and cv.structured_cv is not None
                else None
            ),
        )


class CVOptimizeRequest(BaseModel):
    job_description: str = Field(
        ...,
        min_length=1,
        description="Texto de la oferta laboral.",
        validation_alias=AliasChoices("job_description", "job_description_text"),
    )


class CVOptimizeResponse(BaseModel):
    optimized_content: str
    optimized_body: str
    original_variance_score: float
    optimized_variance_score: float
    writer_attempts: int
    is_within_threshold: bool
    original_ic: float | None
    optimized_ic: float | None
    original_per_dimension: dict[str, float]
    optimized_per_dimension: dict[str, float]
    gap_report: str
    personal_info: dict[str, object] | None

    @classmethod
    def from_domain(cls, optimized: OptimizedCV) -> CVOptimizeResponse:
        return cls(
            optimized_content=optimized.full_content,
            optimized_body=optimized.content,
            original_variance_score=optimized.original_variance_score,
            optimized_variance_score=optimized.optimized_variance_score,
            writer_attempts=optimized.writer_attempts,
            is_within_threshold=optimized.is_within_threshold(),
            original_ic=optimized.original_ic,
            optimized_ic=optimized.optimized_ic,
            original_per_dimension=optimized.original_per_dimension,
            optimized_per_dimension=optimized.optimized_per_dimension,
            gap_report=optimized.gap_report,
            personal_info=(
                optimized.personal_info.to_dict()
                if optimized.personal_info is not None
                else None
            ),
        )
