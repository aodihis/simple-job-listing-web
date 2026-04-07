from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.logging.config import get_logger
from app.models.refresh_token import RefreshToken
from app.models.user import AdminUser
from app.schemas.auth import RegisterRequest
from app.utils.exceptions import ConflictError, UnauthorizedError
from app.utils.security import generate_refresh_token, hash_password, hash_refresh_token, verify_password

settings = get_settings()

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


def issue_refresh_token(db: Session, user: AdminUser) -> str:
    """
    Generate a refresh token, persist a hashed copy in the DB, and return the raw token.
    """
    raw_token = generate_refresh_token()
    token_hash = hash_refresh_token(raw_token)
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    record = RefreshToken(
        token_hash=token_hash,
        user_id=user.id,
        expires_at=expires_at,
        revoked=False,
    )
    db.add(record)
    db.flush()

    log.info("auth.refresh_token_issued", user_id=user.public_id)
    return raw_token


def rotate_refresh_token(db: Session, raw_token: str) -> tuple[AdminUser, str]:
    """
    Validate the refresh token, revoke it (token rotation), issue a new one, and return
    (user, new_raw_token).

    Raises:
        UnauthorizedError: If the token is not found, revoked, or expired, or the user is inactive.
    """
    token_hash = hash_refresh_token(raw_token)
    record = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    if record is None:
        log.warning("auth.refresh_failed", reason="token_not_found")
        raise UnauthorizedError("Invalid refresh token.")

    if record.revoked:
        log.warning("auth.refresh_failed", reason="token_revoked", user_id=record.user.public_id)
        raise UnauthorizedError("Refresh token has been revoked.")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if record.expires_at < now:
        log.warning("auth.refresh_failed", reason="token_expired", user_id=record.user.public_id)
        raise UnauthorizedError("Refresh token has expired.")

    user = record.user
    if not user.is_active:
        log.warning("auth.refresh_failed", reason="account_inactive", user_id=user.public_id)
        raise UnauthorizedError("This account has been deactivated.")

    # Revoke the used token (token rotation — prevents replay)
    record.revoked = True
    db.flush()

    new_raw_token = issue_refresh_token(db, user)
    log.info("auth.refresh_success", user_id=user.public_id)
    return user, new_raw_token
