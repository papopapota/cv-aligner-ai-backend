from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.out.user_port import UserRepositoryPort
from src.domain.entities.user import User
from src.domain.errors import UserAlreadyExistsError
from src.infrastructure.adapters.out.repositories.models import UserModel


class SQLAlchemyUserRepository(UserRepositoryPort):
    """Implementation of UserRepositoryPort using SQLAlchemy 2.0 async sessions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(model: UserModel) -> User:
        return User(
            id=model.id,
            name=model.name,
            email=model.email,
            password=model.password,
            created_at=model.created_at,
        )

    async def get_by_id(self, user_id: int) -> User | None:
        model = await self._session.get(UserModel, user_id)
        if model is None:
            return None
        return self._to_domain(model)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def create(self, name: str, email: str, password: str) -> User:
        model = UserModel(name=name, email=email, password=password)
        self._session.add(model)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise UserAlreadyExistsError(email) from None
        await self._session.refresh(model)
        return self._to_domain(model)

    async def update(self, user: User) -> User:
        model = await self._session.get(UserModel, user.id)
        if model is None:
            return user
        model.name = user.name
        model.email = user.email
        model.password = user.password
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise UserAlreadyExistsError(user.email) from None
        await self._session.refresh(model)
        return self._to_domain(model)

    async def delete(self, user_id: int) -> None:
        model = await self._session.get(UserModel, user_id)
        if model is None:
            return
        await self._session.delete(model)
        await self._session.commit()
