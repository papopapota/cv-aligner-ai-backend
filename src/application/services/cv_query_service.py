from uuid import UUID

from src.application.ports.inbound.cv_query_use_case import CVQueryUseCase
from src.application.ports.out.cv_repository_port import CVRepositoryPort
from src.domain.entities.cv import CV
from src.domain.errors import CVNotFoundError


class CVQueryService(CVQueryUseCase):
    def __init__(self, repository: CVRepositoryPort) -> None:
        self._repository = repository

    async def get(self, cv_id: UUID, user_id: int) -> CV:
        cv = await self._repository.get_by_id(cv_id, user_id)
        if cv is None:
            raise CVNotFoundError(f"The CV '{cv_id}' does not exist.")
        return cv

    async def list(self, user_id: int) -> list[CV]:
        return await self._repository.list_by_user(user_id)
