from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import AdminUser
from app.schemas.auth import AdminUserRead, LoginRequest, RegisterRequest, TokenResponse
from app.services import auth_service
from app.utils.security import create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
settings = get_settings()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=201,
    summary="Register the first admin account",
    description=(
        "Create the initial admin account. Succeeds only when no admin accounts exist yet. "
        "Returns a JWT access token. Subsequent admins must be invited by an existing admin."
    ),
)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = auth_service.register_first_admin(db, body)
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=user.public_id)
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in as an admin",
    description="Authenticate with email and password. Returns a JWT access token.",
)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = auth_service.authenticate_user(db, body.email, body.password)
    token = create_access_token(subject=user.public_id)
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/me",
    response_model=AdminUserRead,
    summary="Get current admin profile",
    description="Returns the authenticated admin's profile. Requires a valid JWT token.",
)
def me(current_user: AdminUser = Depends(get_current_user)) -> AdminUserRead:
    return AdminUserRead.model_validate(current_user)
