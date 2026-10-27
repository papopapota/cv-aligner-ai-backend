from __future__ import annotations

import asyncpg
from datetime import datetime

from src.application.ports.out.user_port import UserRepositoryPort
from src.domain.entities.user import User


class AsyncpgUserRepository(UserRepositoryPort):
    """Implementation of UserRepositoryPort using asyncpg for PostgreSQL."""

    def __init__(self, dsn: str | None = None) -> None:
        """
        Initialize the repository.

        Args:
            dsn: Database connection string. If None, uses environment variables:
                DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
        """
        self._dsn = dsn or (
            "postgresql://postgres:postgresql@localhost:5432/cvaligner"
        )

    async def _get_connection(self) -> asyncpg.Connection:
        return await asyncpg.connect(self._dsn)

    async def _close_connection(self, conn: asyncpg.Connection) -> None:
        await conn.close()

    async def get_by_id(self, user_id: int) -> User | None:
        conn = await self._get_connection()
        try:
            row = await conn.fetchrow(
                "SELECT id, name, email, password, created_at FROM Users WHERE id = $1",
                user_id,
            )
            if row is None:
                return None
            return User(
                id=row["id"],
                name=row["name"],
                email=row["email"],
                password=row["password"],
                created_at=row["created_at"],
            )
        finally:
            await self._close_connection(conn)

    async def get_by_email(self, email: str) -> User | None:
        conn = await self._get_connection()
        try:
            row = await conn.fetchrow(
                "SELECT id, name, email, password, created_at FROM Users WHERE email = $1",
                email,
            )
            if row is None:
                return None
            return User(
                id=row["id"],
                name=row["name"],
                email=row["email"],
                password=row["password"],
                created_at=row["created_at"],
            )
        finally:
            await self._close_connection(conn)

    async def create(self, name: str, email: str, password: str) -> User:
        conn = await self._get_connection()
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO Users (name, email, password, created_at)
                VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                RETURNING id, name, email, password, created_at
                """,
                name,
                email,
                password,
            )
            return User(
                id=row["id"],
                name=row["name"],
                email=row["email"],
                password=row["password"],
                created_at=row["created_at"],
            )
        finally:
            await self._close_connection(conn)

    async def update(self, user: User) -> User:
        conn = await self._get_connection()
        try:
            await conn.execute(
                """
                UPDATE Users
                SET name = $1, email = $2, password = $3
                WHERE id = $4
                """,
                user.name,
                user.email,
                user.password,
                user.id,
            )
            return user
        finally:
            await self._close_connection(conn)

    async def delete(self, user_id: int) -> None:
        conn = await self._get_connection()
        try:
            await conn.execute(
                "DELETE FROM Users WHERE id = $1",
                user_id,
            )
        finally:
            await self._close_connection(conn)