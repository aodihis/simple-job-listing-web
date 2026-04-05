from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import AdminUser
from app.utils.exceptions import UnauthorizedError
from app.utils.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AdminUser:
    """
    Decode the JWT Bearer token and return the matching active admin user.

    Raises:
        UnauthorizedError: If the token is missing, invalid, expired,
                           or the user is not found / inactive.
    """
    if credentials is None:
        raise UnauthorizedError("Authentication required.")

    payload = decode_token(credentials.credentials)
    user_public_id: str | None = payload.get("sub")

    if not user_public_id:
        raise UnauthorizedError("Invalid token payload.")

    user = db.query(AdminUser).filter(AdminUser.public_id == user_public_id).first()

    if user is None:
        raise UnauthorizedError("User not found.")

    if not user.is_active:
        raise UnauthorizedError("This account has been deactivated.")

    return user


def require_active_admin(
    current_user: AdminUser = Depends(get_current_user),
) -> AdminUser:
    """Alias for get_current_user — use this on all admin-only endpoints for clarity."""
    return current_user
