"""
Unit tests for app.utils.security — password hashing and JWT utilities.
These are pure unit tests; no database or HTTP client needed.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from jose import jwt

from app.config import get_settings
from app.utils.exceptions import UnauthorizedError
from app.utils.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)

settings = get_settings()


# ── Password hashing ──────────────────────────────────────────────────────────

class TestHashPassword:
    def test_returns_string(self) -> None:
        result = hash_password("mysecretpassword")
        assert isinstance(result, str)

    def test_hash_is_not_plaintext(self) -> None:
        plain = "mysecretpassword"
        assert hash_password(plain) != plain

    def test_two_hashes_of_same_password_differ(self) -> None:
        """bcrypt uses a random salt so the same password yields different hashes."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2

    def test_hash_starts_with_bcrypt_prefix(self) -> None:
        h = hash_password("abc123")
        assert h.startswith("$2b$") or h.startswith("$2a$")


class TestVerifyPassword:
    def test_correct_password_returns_true(self) -> None:
        plain = "correct-horse-battery-staple"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_wrong_password_returns_false(self) -> None:
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_empty_password_vs_hash_of_empty_returns_true(self) -> None:
        hashed = hash_password("")
        assert verify_password("", hashed) is True

    def test_empty_password_vs_nonempty_hash_returns_false(self) -> None:
        hashed = hash_password("nonempty")
        assert verify_password("", hashed) is False

    def test_case_sensitive(self) -> None:
        hashed = hash_password("Password123")
        assert verify_password("password123", hashed) is False
        assert verify_password("PASSWORD123", hashed) is False


# ── JWT creation ──────────────────────────────────────────────────────────────

class TestCreateAccessToken:
    def test_returns_string(self) -> None:
        token = create_access_token("user-public-id")
        assert isinstance(token, str)

    def test_token_contains_sub_claim(self) -> None:
        subject = "abc-123-def"
        token = create_access_token(subject)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == subject

    def test_token_contains_exp_claim(self) -> None:
        token = create_access_token("user-id")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload

    def test_custom_expiry_is_respected(self) -> None:
        from datetime import datetime, timezone
        delta = timedelta(minutes=5)
        before = datetime.now(timezone.utc)
        token = create_access_token("user-id", expires_delta=delta)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        after = datetime.now(timezone.utc)
        # JWT exp is stored as a Unix integer (truncated to seconds), so allow 1s tolerance.
        assert before + delta - timedelta(seconds=1) <= exp <= after + delta + timedelta(seconds=1)

    def test_different_subjects_produce_different_tokens(self) -> None:
        t1 = create_access_token("user-1")
        t2 = create_access_token("user-2")
        assert t1 != t2


# ── JWT decoding ──────────────────────────────────────────────────────────────

class TestDecodeToken:
    def test_decodes_valid_token(self) -> None:
        token = create_access_token("user-xyz")
        payload = decode_token(token)
        assert payload["sub"] == "user-xyz"

    def test_raises_for_invalid_token(self) -> None:
        with pytest.raises(UnauthorizedError):
            decode_token("this.is.not.valid")

    def test_raises_for_tampered_token(self) -> None:
        token = create_access_token("user-id")
        # flip the last character to tamper with the signature
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        with pytest.raises(UnauthorizedError):
            decode_token(tampered)

    def test_raises_for_expired_token(self) -> None:
        token = create_access_token("user-id", expires_delta=timedelta(seconds=-1))
        with pytest.raises(UnauthorizedError):
            decode_token(token)

    def test_raises_for_wrong_secret(self) -> None:
        # Encode with a different secret
        payload = {"sub": "user-id"}
        bad_token = jwt.encode(payload, "wrong-secret", algorithm=settings.ALGORITHM)
        with pytest.raises(UnauthorizedError):
            decode_token(bad_token)

    def test_raises_for_empty_string(self) -> None:
        with pytest.raises(UnauthorizedError):
            decode_token("")

    def test_returned_payload_contains_sub(self) -> None:
        token = create_access_token("my-subject")
        payload = decode_token(token)
        assert "sub" in payload
        assert payload["sub"] == "my-subject"
