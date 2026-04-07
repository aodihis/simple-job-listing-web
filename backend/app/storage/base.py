"""
Storage backend protocol.

Any storage implementation must satisfy this interface.
Add a new class in its own module, implement these three methods,
then register it in __init__.py's get_storage() factory.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    def upload(self, key: str, content: bytes) -> None:
        """
        Persist *content* at the given *key*.

        The key is an opaque path string (e.g. ``cv/<uuid>/resume.pdf``).
        Implementations must create any intermediate directories/prefixes.
        """
        ...

    def download(self, key: str) -> bytes:
        """
        Return the raw bytes stored at *key*.

        Raises FileNotFoundError if the key does not exist.
        """
        ...

    def delete(self, key: str) -> None:
        """
        Remove the object at *key*.

        Must not raise if the key does not exist (idempotent).
        """
        ...
