from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.inbound.cv_optimization_use_case import (
    CVOptimizationUseCase,
)
from src.application.ports.inbound.cv_query_use_case import CVQueryUseCase
from src.application.ports.inbound.cv_upload_use_case import (
    CVUploadUseCase,
    FileUpload,
)
from src.application.ports.out.cv_repository_port import CVRepositoryPort
from src.composition import (
    build_cv_optimization_use_case,
    build_cv_query_use_case,
    build_cv_repository,
    build_cv_upload_use_case,
    build_file_storage,
    build_orchestrator,
    process_cv_in_background,
)
from src.domain.entities.user import User
from src.infrastructure.adapters.inbound.api.dto.cv_dto import (
    CVContentResponse,
    CVOptimizeRequest,
    CVOptimizeResponse,
    CVStatusResponse,
    CVUploadResponse,
)
from src.infrastructure.adapters.inbound.api.routers.auth_router import (
    get_current_user,
)
from src.infrastructure.database import get_session

router = APIRouter(prefix="/cvs", tags=["CVs"])


def get_cv_repository(
    session: AsyncSession = Depends(get_session),
) -> CVRepositoryPort:
    return build_cv_repository(session)


def get_cv_query_use_case(
    repository: CVRepositoryPort = Depends(get_cv_repository),
) -> CVQueryUseCase:
    return build_cv_query_use_case(repository)


def get_cv_upload_use_case(
    repository: CVRepositoryPort = Depends(get_cv_repository),
) -> CVUploadUseCase:
    return build_cv_upload_use_case(repository, build_file_storage())


def get_cv_optimization_use_case(
    repository: CVRepositoryPort = Depends(get_cv_repository),
) -> CVOptimizationUseCase:
    return build_cv_optimization_use_case(repository, build_orchestrator())


def get_cv_processing_task() -> Callable[[UUID], Awaitable[None]]:
    return process_cv_in_background


@router.post(
    "",
    response_model=CVUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a CV",
)
async def upload_cv(
    background_tasks: BackgroundTasks,
    cv_file: Annotated[UploadFile, File(...)],
    current_user: User = Depends(get_current_user),
    use_case: CVUploadUseCase = Depends(get_cv_upload_use_case),
    processing_task: Callable[[UUID], Awaitable[None]] = Depends(
        get_cv_processing_task
    ),
) -> CVUploadResponse:
    content = await cv_file.read()
    cv = await use_case.execute(
        FileUpload(
            filename=cv_file.filename or "",
            content_type=cv_file.content_type or "",
            content=content,
        ),
        current_user.id,
    )
    background_tasks.add_task(processing_task, cv.id)
    return CVUploadResponse.from_domain(cv)


@router.get(
    "",
    response_model=list[CVStatusResponse],
    summary="List the current user's CVs",
)
async def list_cvs(
    current_user: User = Depends(get_current_user),
    use_case: CVQueryUseCase = Depends(get_cv_query_use_case),
) -> list[CVStatusResponse]:
    cvs = await use_case.list(current_user.id)
    return [CVStatusResponse.from_domain(cv) for cv in cvs]


@router.get(
    "/{cv_id}",
    response_model=CVStatusResponse,
    summary="Get the status of a CV",
)
async def get_cv(
    cv_id: UUID,
    current_user: User = Depends(get_current_user),
    use_case: CVQueryUseCase = Depends(get_cv_query_use_case),
) -> CVStatusResponse:
    cv = await use_case.get(cv_id, current_user.id)
    return CVStatusResponse.from_domain(cv)


@router.get(
    "/{cv_id}/content",
    response_model=CVContentResponse,
    response_model_exclude_none=True,
    summary="Get the extracted content of a parsed CV",
)
async def get_cv_content(
    cv_id: UUID,
    include_structured: bool = Query(
        False,
        description="Include the structured CV JSON in the response.",
    ),
    current_user: User = Depends(get_current_user),
    use_case: CVQueryUseCase = Depends(get_cv_query_use_case),
) -> CVContentResponse:
    cv = await use_case.get_content(cv_id, current_user.id)
    return CVContentResponse.from_domain(
        cv,
        include_structured=include_structured,
    )


@router.post(
    "/{cv_id}/optimize",
    response_model=CVOptimizeResponse,
    summary="Optimize a parsed CV",
)
async def optimize_cv(
    cv_id: UUID,
    payload: CVOptimizeRequest,
    current_user: User = Depends(get_current_user),
    use_case: CVOptimizationUseCase = Depends(get_cv_optimization_use_case),
) -> CVOptimizeResponse:
    optimized = await use_case.execute(
        cv_id,
        current_user.id,
        payload.job_description,
    )
    return CVOptimizeResponse.from_domain(optimized)
