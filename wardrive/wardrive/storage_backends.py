"""
Custom S3/MinIO storage backend that normalizes object keys and tolerates MinIO
HeadObject 400 (treat as "not exists") so uploads can complete.
"""
import re

from botocore.exceptions import ClientError
from storages.backends.s3 import S3Storage


def _normalize_s3_key(name):
    """Return a key safe for S3/MinIO: no leading slash, no backslashes, no empty segments."""
    if not name or not str(name).strip():
        return "upload"
    name = str(name).replace("\\", "/").strip().lstrip("/")
    parts = [p for p in name.split("/") if p.strip()]
    name = "/".join(parts) if parts else "upload"
    # ASCII-safe key: avoid non-ASCII and problematic chars MinIO may reject
    name = re.sub(r"[^\w\s.\-/]", "_", name)
    name = re.sub(r"\s+", "_", name).strip("_/") or "upload"
    return name.encode("ascii", "ignore").decode("ascii") or "upload"


class MinIOS3Storage(S3Storage):
    """S3 storage that normalizes keys and treats MinIO HeadObject 400 as "not exists"."""

    def get_available_name(self, name, max_length=None):
        name = _normalize_s3_key(name)
        return super().get_available_name(name, max_length=max_length)

    def exists(self, name):
        name = _normalize_s3_key(name)
        try:
            return super().exists(name)
        except ClientError as e:
            # MinIO sometimes returns 400 on HeadObject; treat as "not exists" so upload can proceed
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("400", "BadRequest"):
                return False
            raise
