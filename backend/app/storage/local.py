"""Local filesystem storage backend."""
from __future__ import annotations

import pathlib

from app.logging.config import get_logger

log = get_logger(__name__)


class LocalStorageBackend:
    """
    Stores files on the local filesystem under a configurable root directory.

    Configure via ``STORAGE_LOCAL_DIR`` in your ``.env``.
    The directory is created automatically on first use.
    """

    def __init__(self, root: str) -> None:
        self._root = pathlib.Path(root).resolve()

    def upload(self, key: str, content: bytes) -> None:
        dest = self._root / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        log.info("storage.local.uploaded", key=key, size=len(content))

    def download(self, key: str) -> bytes:
        path = self._root / key
        if not path.exists():
            raise FileNotFoundError(f"Object not found in local storage: {key}")
        data = path.read_bytes()
        log.info("storage.local.downloaded", key=key, size=len(data))
        return data

    def delete(self, key: str) -> None:
        path = self._root / key
        if path.exists():
            path.unlink()
            log.info("storage.local.deleted", key=key)
