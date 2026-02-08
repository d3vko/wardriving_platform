"""
S3/MinIO client singleton for use across the project.
Only instantiated when USE_S3_STORAGE is True and credentials are set.
"""
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_s3_client: Optional[Any] = None


def get_s3_client() -> Optional[Any]:
    """
    Returns the single (singleton) S3/MinIO client instance.
    Lazy initialization: connects only on first use when USE_S3_STORAGE is enabled
    and AWS_S3_ENDPOINT_URL + credentials are set.

    Returns:
        boto3 S3 client instance if configured, None otherwise.
    """
    global _s3_client
    if _s3_client is not None:
        return _s3_client

    from django.conf import settings

    if not getattr(settings, "USE_S3_STORAGE", False):
        return None
    endpoint = getattr(settings, "AWS_S3_ENDPOINT_URL", None)
    if not endpoint:
        return None
    access_key = (getattr(settings, "AWS_ACCESS_KEY_ID", None) or "").strip()
    secret_key = (getattr(settings, "AWS_SECRET_ACCESS_KEY", None) or "").strip()
    if not access_key or not secret_key:
        return None

    try:
        import boto3

        region = getattr(settings, "AWS_S3_REGION_NAME", "us-east-1")
        _s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        return _s3_client
    except Exception as e:
        logger.warning("Could not create S3 client: %s", e)
        return None


def _ensure_bucket(client: Any, bucket: str, region: str) -> None:
    from botocore.exceptions import ClientError

    try:
        client.head_bucket(Bucket=bucket)
        return
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code != "404":
            logger.warning("S3 head_bucket %s failed: %s", bucket, e)
            return
    try:
        if region == "us-east-1":
            client.create_bucket(Bucket=bucket)
        else:
            client.create_bucket(
                Bucket=bucket,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        logger.info("Created S3/MinIO bucket: %s", bucket)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in (
            "BucketAlreadyOwnedByYou",
            "BucketAlreadyExists",
        ):
            return
        logger.warning("S3 create_bucket %s failed: %s", bucket, e)


def ensure_media_bucket() -> None:
    """
    Create the two S3/MinIO buckets if they do not exist:
    - Wardrive bucket (AWS_STORAGE_BUCKET_NAME): uploads from wardrive container.
    - CTFd bucket (CTFD_S3_BUCKET): uploads from CTFd container.
    Call at startup when USE_S3_STORAGE is True.
    """
    client = get_s3_client()
    if client is None:
        return

    from django.conf import settings

    region = getattr(settings, "AWS_S3_REGION_NAME", "us-east-1")
    wardrive_bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "media")
    ctfd_bucket = getattr(settings, "CTFD_S3_BUCKET", "ctfd")

    try:
        _ensure_bucket(client, wardrive_bucket, region)
        _ensure_bucket(client, ctfd_bucket, region)
    except Exception as e:
        logger.warning("Could not ensure wardrive/ctfd buckets: %s", e)
