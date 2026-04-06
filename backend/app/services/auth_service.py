from __future__ import annotations

from sqlalchemy.orm import Session

from app.logging.config import get_logger
from app.models.user import AdminUser
from app.schemas.auth import RegisterRequest
from app.utils.exceptions import ConflictError, UnauthorizedError
from app.utils.security import hash_password, verify_password

log = get_logger(__name__)


def register_first_admin(db: Session, data: RegisterRequest) -> AdminUser:
    """
    Register the very first admin account.

    Raises:
        ConflictError: If any admin account already exists.
    """
    existing_count = db.query(AdminUser).count()
    if existing_count > 0:
        log.warning("auth.register_blocked", reason="admin_already_exists")
        raise ConflictError(
            "An admin account already exists. "
            "Ask an existing admin to invite you, or log in."
        )

    user = AdminUser(
        email=data.email,
        display_name=data.display_name,
        password_hash=hash_password(data.password),
        is_active=True,
        invited_by_id=None,
    )
    db.add(user)
    db.flush()  # populate public_id before caller uses it for JWT

    log.info("auth.register_success", email=data.email)
    return user


def authenticate_user(db: Session, email: str, password: str) -> AdminUser:
    """
    Verify credentials and return the matching active admin.

    Raises:
        UnauthorizedError: If the email is not found, the password is wrong,
                           or the account is inactive.
    """
    user = db.query(AdminUser).filter(AdminUser.email == email).first()

    if user is None:
        log.warning("auth.login_failed", email=email, reason="email_not_found")
        raise UnauthorizedError("Invalid email or password.")

    if not verify_password(password, user.password_hash):
        log.warning("auth.login_failed", email=email, reason="invalid_password")
        raise UnauthorizedError("Invalid email or password.")

    if not user.is_active:
        log.warning("auth.login_failed", email=email, reason="account_inactive")
        raise UnauthorizedError("This account has been deactivated.")

    log.info("auth.login_success", email=email, user_id=user.public_id)
    return user
