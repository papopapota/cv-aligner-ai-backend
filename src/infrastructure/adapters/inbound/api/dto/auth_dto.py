from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    name: str
    email: EmailStr
    password: str

    class ConfigDict:
        json_schema_extra = {
            "example": {
                "name": "Juan Perez",
                "email": "juan@example.com",
                "password": "securepassword123",
            }
        }

class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr
    password: str

    class ConfigDict:
        json_schema_extra = {
            "example": {
                "email": "juan@example.com",
                "password": "securepassword123",
            }
        }

class UserResponse(BaseModel):
    """Response schema for user data."""

    id: int
    name: str
    email: EmailStr
    created_at: datetime

    class ConfigDict:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Juan Perez",
                "email": "juan@example.com",
                "created_at": "2024-01-15T10:30:00Z",
            }
        }

class TokenResponse(BaseModel):
    """Response schema for authentication token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None

    class ConfigDict:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }