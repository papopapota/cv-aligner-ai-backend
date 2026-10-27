from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from bcrypt import checkpw, gensalt, hashpw
from jwt import decode, encode


class SecuritySettings:
    """Configuration for security settings."""

    secret_key: str = secrets.token_urlsafe(32)
    algorithm: str = "HS256"
    access_token_expires_minutes: int = 30
    refresh_token_expires_days: int = 7


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
    Verify a plain text password against a bcrypt hash.

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
    algorithm: str = settings.algorithm,
    secret_key: str = settings.secret_key,
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
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expires_minutes
        )

    to_encode = {"exp": expire, "sub": str(subject)}

    encoded_jwt = encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


def decode_access_token(
    token: str,
    algorithm: str = settings.algorithm,
    secret_key: str = settings.secret_key,
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
    decoded = decode(token, secret_key, algorithms=[algorithm])
    return decoded
