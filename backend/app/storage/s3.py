"""AWS S3 storage backend.

Requires the ``boto3`` package::

    pip install -e ".[s3]"

Configure via environment variables (see ``.env.example``):

    STORAGE_BACKEND=s3
    STORAGE_S3_BUCKET=my-bucket
    STORAGE_S3_REGION=us-east-1
    STORAGE_S3_PREFIX=uploads          # optional key prefix / folder
    STORAGE_S3_ACCESS_KEY_ID=...       # omit to use IAM role / instance profile
    STORAGE_S3_SECRET_ACCESS_KEY=...
"""
from __future__ import annotations

from app.logging.config import get_logger

log = get_logger(__name__)


class S3StorageBackend:
    """
    Stores files in an AWS S3 bucket.

    Authentication falls back to the standard boto3 credential chain
    (environment variables → ~/.aws/credentials → IAM role) when
    ``access_key_id`` / ``secret_access_key`` are not supplied explicitly.
    """

    def __init__(
        self,
        bucket: str,
        *,
        region: str | None = None,
        prefix: str = "",
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise ImportError(
                "boto3 is required for S3 storage. "
                "Install it with: pip install -e '.[s3]'"
            ) from exc

        self._bucket = bucket
        self._prefix = prefix.rstrip("/")

        kwargs: dict[str, str] = {}
        if region:
            kwargs["region_name"] = region
        if access_key_id:
            kwargs["aws_access_key_id"] = access_key_id
        if secret_access_key:
            kwargs["aws_secret_access_key"] = secret_access_key

        self._client = boto3.client("s3", **kwargs)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _full_key(self, key: str) -> str:
        """Prepend the configured prefix to the caller-supplied key."""
        return f"{self._prefix}/{key}" if self._prefix else key

    # ── Protocol implementation ───────────────────────────────────────────────

    def upload(self, key: str, content: bytes) -> None:
        full_key = self._full_key(key)
        self._client.put_object(Bucket=self._bucket, Key=full_key, Body=content)
        log.info("storage.s3.uploaded", key=full_key, bucket=self._bucket, size=len(content))

    def download(self, key: str) -> bytes:
        import botocore.exceptions  # boto3 sub-package, always available if boto3 is installed

        full_key = self._full_key(key)
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=full_key)
            data: bytes = response["Body"].read()
        except botocore.exceptions.ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code in ("NoSuchKey", "404"):
                raise FileNotFoundError(f"Object not found in S3: {full_key}") from exc
            raise

        log.info("storage.s3.downloaded", key=full_key, bucket=self._bucket, size=len(data))
        return data

    def delete(self, key: str) -> None:
        full_key = self._full_key(key)
        # S3 delete_object is idempotent — no error if key is missing
        self._client.delete_object(Bucket=self._bucket, Key=full_key)
        log.info("storage.s3.deleted", key=full_key, bucket=self._bucket)
