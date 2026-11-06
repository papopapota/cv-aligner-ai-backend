from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.out.application_repository import ApplicationRepositoryPort
from src.application.schemas import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationStatusUpdate,
)
from src.application.use_cases import ApplicationUseCase
from src.domain.entities.user import User
from src.infrastructure.adapters.inbound.api.routers.auth_router import get_current_user
from src.infrastructure.adapters.out.application_repository import (
    SQLAlchemyApplicationRepository,
)
from src.infrastructure.database import get_session

router = APIRouter(prefix="/applications", tags=["Applications"])


def get_application_repository(
    session: AsyncSession = Depends(get_session),
) -> ApplicationRepositoryPort:
    return SQLAlchemyApplicationRepository(session)


def get_application_use_case(
    repository: ApplicationRepositoryPort = Depends(get_application_repository),
) -> ApplicationUseCase:
    """Dependency to get ApplicationUseCase."""
    return ApplicationUseCase(repository)


@router.post("", response_model=ApplicationResponse, status_code=201)
async def create_application(
    data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    use_case: ApplicationUseCase = Depends(get_application_use_case),
) -> ApplicationResponse:
    """Create a new application owned by the authenticated user."""
    return await use_case.create_application(current_user.id, data)


@router.get("", response_model=list[ApplicationResponse])
async def list_applications(
    current_user: User = Depends(get_current_user),
    use_case: ApplicationUseCase = Depends(get_application_use_case),
) -> list[ApplicationResponse]:
    """List the applications owned by the authenticated user."""
    return await use_case.list_applications(current_user.id)


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    application_id: int,
    data: ApplicationStatusUpdate,
    current_user: User = Depends(get_current_user),
    use_case: ApplicationUseCase = Depends(get_application_use_case),
) -> ApplicationResponse:
    """Update the status of an application owned by the authenticated user."""
    application = await use_case.update_application_status(
        application_id,
        current_user.id,
        data.status,
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    use_case: ApplicationUseCase = Depends(get_application_use_case),
) -> Response:
    """Delete an application owned by the authenticated user."""
    deleted = await use_case.delete_application(application_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Application not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
