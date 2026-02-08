"""
Consumption of the core S3/storage service.
Re-exports ensure_media_bucket so files app code and ready() keep the same import path.
"""
from apps.core.services import ensure_media_bucket

__all__ = ["ensure_media_bucket"]
