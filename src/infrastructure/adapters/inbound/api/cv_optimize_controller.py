from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from src.application.ports.inbound.optimize_cv_use_case import OptimizeCVUseCase
from src.application.ports.inbound.upload_cv_use_case import (
    FileUpload,
    UploadCVUseCase,
)
from src.composition import (
    build_optimize_cv_use_case,
    build_upload_cv_use_case,
)
from src.infrastructure.adapters.inbound.api.dto.cv_optimize_dto import (
    CVOptimizeResponse,
)

router = APIRouter(tags=["cv"])

OptimizeCVUseCaseDep = Annotated[OptimizeCVUseCase, Depends(build_optimize_cv_use_case)]
UploadCVUseCaseDep = Annotated[UploadCVUseCase, Depends(build_upload_cv_use_case)]


@router.post("/cv/optimize", response_model=CVOptimizeResponse)
async def optimize_cv(
    cv_file: Annotated[UploadFile, File(...)],
    job_description_file: Annotated[UploadFile, File(...)],
    upload_use_case: UploadCVUseCaseDep,
    optimize_use_case: OptimizeCVUseCaseDep,
) -> CVOptimizeResponse:
    candidate, job_description = await upload_use_case.execute(
        cv=FileUpload(
            filename=cv_file.filename or "",
            content_type=cv_file.content_type or "",
            content=await cv_file.read(),
        ),
        job_description=FileUpload(
            filename=job_description_file.filename or "",
            content_type=job_description_file.content_type or "",
            content=await job_description_file.read(),
        ),
    )

    optimized = await optimize_use_case.execute(candidate, job_description)

    return CVOptimizeResponse(
        optimized_content=optimized.content,
        variance_score=optimized.variance_score,
        writer_attempts=optimized.writer_attempts,
        is_within_threshold=optimized.is_within_threshold(),
    )
