from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings
from app.utils.exceptions import UnauthorizedError

settings = get_settings()


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject: The token subject — typically the user's public_id.
        expires_delta: Custom expiry. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES from settings.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Raises:
        UnauthorizedError: If the token is invalid, expired, or malformed.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired token.") from exc


def generate_refresh_token() -> str:
    """Return a cryptographically random URL-safe token string (48 bytes → 64 chars)."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw_token: str) -> str:
    """Return the SHA-256 hex digest of a raw refresh token for safe DB storage."""
    return hashlib.sha256(raw_token.encode()).hexdigest()
