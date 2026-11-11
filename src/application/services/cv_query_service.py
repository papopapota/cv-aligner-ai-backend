from uuid import UUID

from src.application.ports.inbound.cv_query_use_case import CVQueryUseCase
from src.application.ports.out.cv_repository_port import CVRepositoryPort
from src.domain.entities.cv import CV
from src.domain.errors import CVFailedError, CVNotFoundError, CVNotReadyError


class CVQueryService(CVQueryUseCase):
    def __init__(self, repository: CVRepositoryPort) -> None:
        self._repository = repository

    async def get(self, cv_id: UUID, user_id: int) -> CV:
        cv = await self._repository.get_status_by_id(cv_id, user_id)
        if cv is None:
            raise CVNotFoundError(f"The CV '{cv_id}' does not exist.")
        return cv

    async def list(self, user_id: int) -> list[CV]:
        return await self._repository.list_status_by_user(user_id)

    async def get_content(self, cv_id: UUID, user_id: int) -> CV:
        cv = await self._repository.get_by_id(cv_id, user_id)
        if cv is None:
            raise CVNotFoundError(f"The CV '{cv_id}' does not exist.")
        if cv.is_failed():
            raise CVFailedError(
                cv.error_code or "PROCESSING_FAILED",
                cv.error_message or "The CV could not be processed.",
            )
        if not cv.is_ready_for_optimization() or not cv.raw_text:
            raise CVNotReadyError("The CV content is not ready yet.")
        return cv
