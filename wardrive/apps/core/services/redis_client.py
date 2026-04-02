"""
Redis client singleton for use across the project.
Only instantiated when REDIS_URL is set; otherwise get_redis_client() returns None.
"""

from typing import Optional

from redis import Redis


_redis_client: Optional[Redis] = None


def get_redis_client() -> Optional[Redis]:
    """
    Returns the single (singleton) Redis client instance.
    Lazy initialization: connects only on first use and when REDIS_URL is valid.

    Returns:
        Redis instance if REDIS_URL is set, None otherwise.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    from django.conf import settings

    redis_url = getattr(settings, "REDIS_URL", "") or ""
    if not redis_url or not redis_url.strip():
        return None

    _redis_client = Redis.from_url(redis_url, decode_responses=False)
    return _redis_client
