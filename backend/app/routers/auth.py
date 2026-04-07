from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import AdminUser
from app.schemas.auth import AdminUserRead, LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.services import auth_service
from app.utils.security import create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
settings = get_settings()


def _build_token_response(user: AdminUser, refresh_token: str) -> TokenResponse:
    access_token = create_access_token(subject=user.public_id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=201,
    summary="Register the first admin account",
    description=(
        "Create the initial admin account. Succeeds only when no admin accounts exist yet. "
        "Returns JWT access and refresh tokens. Subsequent admins must be invited by an existing admin."
    ),
)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = auth_service.register_first_admin(db, body)
    refresh_token = auth_service.issue_refresh_token(db, user)
    return _build_token_response(user, refresh_token)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in as an admin",
    description="Authenticate with email and password. Returns JWT access and refresh tokens.",
)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = auth_service.authenticate_user(db, body.email, body.password)
    refresh_token = auth_service.issue_refresh_token(db, user)
    return _build_token_response(user, refresh_token)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description=(
        "Exchange a valid refresh token for a new access token and a rotated refresh token. "
        "Each refresh token can only be used once (token rotation)."
    ),
)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user, new_refresh_token = auth_service.rotate_refresh_token(db, body.refresh_token)
    return _build_token_response(user, new_refresh_token)


@router.get(
    "/me",
    response_model=AdminUserRead,
    summary="Get current admin profile",
    description="Returns the authenticated admin's profile. Requires a valid JWT token.",
)
def me(current_user: AdminUser = Depends(get_current_user)) -> AdminUserRead:
    return AdminUserRead.model_validate(current_user)
