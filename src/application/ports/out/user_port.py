from __future__ import annotations

from src.domain.entities.user import User


class UserRepositoryPort:
    """Port (interface) for User repository operations.

    Implementations should inherit from this class and implement all abstract methods.
    """

    async def get_by_id(self, user_id: int) -> User | None:
        """Get a user by their ID."""
        raise NotImplementedError

    async def get_by_email(self, email: str) -> User | None:
        """Get a user by their email."""
        raise NotImplementedError

    async def create(self, name: str, email: str, password: str) -> User:
        """Create a new user."""
        raise NotImplementedError

    async def update(self, user: User) -> User:
        """Update an existing user."""
        raise NotImplementedError

    async def delete(self, user_id: int) -> None:
        """Delete a user by ID."""
        raise NotImplementedError