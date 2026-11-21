from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from src.application.ports.inbound.extract_job_description_use_case import (
    ExtractJobDescriptionUseCase,
)
from src.composition import build_extract_job_description_use_case
from src.infrastructure.adapters.inbound.api.dto.job_description_dto import (
    JobDescriptionExtractRequest,
    JobDescriptionExtractResponse,
)

router = APIRouter(prefix="/job-descriptions", tags=["Job descriptions"])


def get_extract_job_description_use_case() -> ExtractJobDescriptionUseCase:
    return build_extract_job_description_use_case()


@router.post(
    "/extract",
    response_model=JobDescriptionExtractResponse,
    summary="Extract a job description from a public URL",
)
async def extract_job_description(
    payload: JobDescriptionExtractRequest,
    use_case: Annotated[
        ExtractJobDescriptionUseCase, Depends(get_extract_job_description_use_case)
    ],
) -> JobDescriptionExtractResponse:
    content = await use_case.execute(payload.url)
    return JobDescriptionExtractResponse(
        title=content.title,
        company=content.company,
        description=content.description,
    )
