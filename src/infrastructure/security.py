from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from bcrypt import checkpw, gensalt, hashpw
from jwt import decode, encode
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecuritySettings(BaseSettings):
    """Configuration for security settings.

    Values are read from the ``JWT_*`` environment variables / ``.env`` file so
    that tokens remain valid across process restarts.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    secret_key: str = Field(
        default="dev-insecure-secret-change-me",
        validation_alias="JWT_SECRET_KEY",
    )
    algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expires_minutes: int = Field(
        default=30,
        validation_alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    refresh_token_expires_days: int = Field(
        default=7,
        validation_alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS",
    )


settings = SecuritySettings()


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string (bcrypt format includes the salt)
    """
    salt = gensalt()
    hashed = hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a bcrypt hash.

    Args:
        plain_password: The plain text password to check
        hashed_password: The bcrypt hash to verify against

    Returns:
        True if the password matches, False otherwise
    """
    return checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
    algorithm: str | None = None,
    secret_key: str | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The token subject (usually user ID or email)
        expires_delta: Time delta until expiration. Defaults to settings.
        algorithm: JWT algorithm. Defaults to settings.
        secret_key: Secret key for signing. Defaults to settings.

    Returns:
        Encoded JWT token string
    """
    resolved_algorithm = algorithm or settings.algorithm
    resolved_secret = secret_key or settings.secret_key

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expires_minutes
        )

    to_encode = {"exp": expire, "sub": str(subject)}

    encoded_jwt = encode(to_encode, resolved_secret, algorithm=resolved_algorithm)
    return encoded_jwt


def decode_access_token(
    token: str,
    algorithm: str | None = None,
    secret_key: str | None = None,
) -> dict[str, Any]:
    """
    Decode a JWT access token.

    Args:
        token: The JWT token string
        algorithm: JWT algorithm. Defaults to settings.
        secret_key: Secret key for verification. Defaults to settings.

    Returns:
        Decoded token payload as dict

    Raises:
        jwt.DecodeError: If the token is invalid or expired
    """
    decoded = decode(
        token,
        secret_key or settings.secret_key,
        algorithms=[algorithm or settings.algorithm],
    )
    return decoded
