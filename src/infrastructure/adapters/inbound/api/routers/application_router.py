from __future__ import annotations

from fastapi import APIRouter, Depends, Query, HTTPException

from src.application.schemas import ApplicationCreate, ApplicationResponse
from src.application.use_cases import ApplicationUseCase
from src.infrastructure.database import async_session_factory

router = APIRouter(prefix="/applications", tags=["Applications"])


def get_application_use_case() -> ApplicationUseCase:
    """Dependency to get ApplicationUseCase."""
    return ApplicationUseCase()


@router.post("/", response_model=ApplicationResponse, status_code=201)
async def create_application(
    data: ApplicationCreate,
    use_case: ApplicationUseCase = Depends(get_application_use_case),
) -> ApplicationResponse:
    """Create a new application.
    
    Requires user_id to associate with a registered user.
    """
    return await use_case.create_application(data)


@router.get("/", response_model=list[ApplicationResponse])
async def list_applications(
    user_id: int = Query(..., description="ID del usuario cuyas postulaciones listar"),
    use_case: ApplicationUseCase = Depends(get_application_use_case),
) -> list[ApplicationResponse]:
    """List applications for a specific user.
    
    Requires user_id parameter to filter applications by registered user.
    """
    return await use_case.list_applications(user_id)


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    application_id: int,
    status: str,
    use_case: ApplicationUseCase = Depends(get_application_use_case),
) -> ApplicationResponse:
    """Update application status."""
    return await use_case.update_application_status(application_id, status)