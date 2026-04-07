"""
Storage abstraction layer.

Usage::

    from app.storage import get_storage

    storage = get_storage()
    storage.upload("cv/abc-123/resume.pdf", file_bytes)
    data = storage.download("cv/abc-123/resume.pdf")
    storage.delete("cv/abc-123/resume.pdf")

The active backend is selected by the ``STORAGE_BACKEND`` env var (default: ``local``).
Call ``reset_storage()`` in tests to clear the cached instance between cases.
"""
from __future__ import annotations

from functools import lru_cache

from app.storage.base import StorageBackend
from app.storage.local import LocalStorageBackend
from app.storage.s3 import S3StorageBackend

__all__ = ["StorageBackend", "LocalStorageBackend", "S3StorageBackend", "get_storage"]


@lru_cache(maxsize=1)
def get_storage() -> StorageBackend:
    """
    Return the singleton storage backend configured via environment variables.

    Cached after the first call — the backend is not re-created on every
    request.  Call ``reset_storage()`` in tests when you need a fresh instance.
    """
    from app.config import get_settings  # local import avoids circular dependency

    settings = get_settings()

    if settings.STORAGE_BACKEND == "s3":
        if not settings.STORAGE_S3_BUCKET:
            raise ValueError(
                "STORAGE_S3_BUCKET must be set when STORAGE_BACKEND=s3"
            )
        return S3StorageBackend(
            bucket=settings.STORAGE_S3_BUCKET,
            region=settings.STORAGE_S3_REGION,
            prefix=settings.STORAGE_S3_PREFIX,
            access_key_id=settings.STORAGE_S3_ACCESS_KEY_ID,
            secret_access_key=settings.STORAGE_S3_SECRET_ACCESS_KEY,
        )

    # default: local
    return LocalStorageBackend(root=settings.STORAGE_LOCAL_DIR)


def reset_storage() -> None:
    """Clear the cached storage instance. Call this in test teardown."""
    get_storage.cache_clear()
