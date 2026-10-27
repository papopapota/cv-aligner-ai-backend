from fastapi import APIRouter, Depends, HTTPException, status

from src.application.ports.out.user_port import UserRepositoryPort
from src.infrastructure.adapters.inbound.api.dto.auth_dto import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from src.infrastructure.adapters.out.repositories.user_repository import AsyncpgUserRepository
from src.infrastructure.security import (
    SecuritySettings,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(tags=["auth"])


# Dependency
def get_user_repository() -> UserRepositoryPort:
    return AsyncpgUserRepository()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    user_data: RegisterRequest,
    repo: UserRepositoryPort = Depends(get_user_repository),
) -> UserResponse:
    """
    Register a new user account.

    - **name**: Full name of the user
    - **email**: Email address (will be made unique)
    - **password**: Plain text password (will be hashed)
    """
    # Check if user already exists
    existing = await repo.get_by_email(user_data.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash password and create user
    hashed_password = hash_password(user_data.password)
    new_user = await repo.create(
        name=user_data.name,
        email=user_data.email,
        password=hashed_password,
    )

    return UserResponse(
        id=new_user.id,
        name=new_user.name,
        email=new_user.email,
        created_at=new_user.created_at,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get access token",
)
async def login(
    login_data: LoginRequest,
    repo: UserRepositoryPort = Depends(get_user_repository),
) -> TokenResponse:
    """
    Login with email and password.

    - **email**: User's email address
    - **password**: Plain text password
    """
    # Find user by email
    user = await repo.get_by_email(login_data.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(login_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(subject=user.email)
    refresh_token = create_access_token(
        subject=user.email,
        expires_delta=None,
    )

    settings = SecuritySettings()

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expires_minutes * 60,
        refresh_token=refresh_token,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(
    token: str,
    repo: UserRepositoryPort = Depends(get_user_repository),
) -> TokenResponse:
    """
    Refresh an access token using a refresh token.

    - **token**: Valid refresh token
    """
    try:
        decoded = decode_access_token(token)
        email = decoded.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Find user
    user = await repo.get_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Create new access token
    access_token = create_access_token(subject=user.email)
    refresh_token = create_access_token(subject=user.email)

    settings = SecuritySettings()

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expires_minutes * 60,
        refresh_token=refresh_token,
    )
