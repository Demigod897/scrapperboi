import io

import structlog
from minio import Minio
from minio.error import S3Error

from config.settings import settings

logger = structlog.get_logger(__name__)

_client: Minio | None = None


def get_minio_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _client


def ensure_bucket():
    """Create the raw storage bucket if it doesn't exist."""
    client = get_minio_client()
    bucket = settings.minio_bucket
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        logger.info("bucket_created", bucket=bucket)


def store_raw_document(content_hash: str, content: bytes, content_type: str = "application/pdf") -> str:
    """Store a raw document in MinIO.

    Args:
        content_hash: SHA-256 hash (used as object key)
        content: Raw file bytes
        content_type: MIME type

    Returns:
        Storage key (object path)
    """
    client = get_minio_client()
    bucket = settings.minio_bucket
    ensure_bucket()

    # Use hash as key with extension
    ext = "pdf" if "pdf" in content_type else "html"
    key = f"raw/{content_hash[:4]}/{content_hash}.{ext}"

    try:
        client.put_object(
            bucket,
            key,
            io.BytesIO(content),
            length=len(content),
            content_type=content_type,
        )
        logger.debug("document_stored", key=key, size=len(content))
        return key
    except S3Error as e:
        logger.error("storage_failed", key=key, error=str(e))
        raise


def get_raw_document(key: str) -> bytes:
    """Retrieve a raw document from MinIO."""
    client = get_minio_client()
    bucket = settings.minio_bucket

    try:
        response = client.get_object(bucket, key)
        content = response.read()
        response.close()
        response.release_conn()
        return content
    except S3Error as e:
        logger.error("retrieval_failed", key=key, error=str(e))
        raise


def document_exists(content_hash: str) -> bool:
    """Check if a document with this hash already exists."""
    client = get_minio_client()
    bucket = settings.minio_bucket

    for ext in ["pdf", "html"]:
        key = f"raw/{content_hash[:4]}/{content_hash}.{ext}"
        try:
            client.stat_object(bucket, key)
            return True
        except S3Error:
            continue

    return False
