"""
Shared utilities (dates, etc.).

Range normalization uses the **calendar day** in the timezone of the incoming datetime: if
*aware*, ``dt.tzinfo`` is used; if *naive*, values are interpreted in
``django.utils.timezone.get_current_timezone()`` (e.g. project ``TIME_ZONE``). DST rules follow
that timezone.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import TYPE_CHECKING

from django.utils import timezone as dj_tz

if TYPE_CHECKING:
    from datetime import tzinfo


def _effective_tz(dt: datetime) -> tzinfo:
    if dt.tzinfo is not None:
        return dt.tzinfo
    return dj_tz.get_current_timezone()


def normalize_range_start(dt: datetime) -> datetime:
    """
    Start of the calendar day (00:00:00) in the effective timezone, as an aware datetime.
    """
    tz = _effective_tz(dt)
    if dj_tz.is_naive(dt):
        local = dj_tz.make_aware(dt, tz)
    else:
        local = dt.astimezone(tz)
    day = local.date()
    return datetime.combine(day, time.min, tzinfo=tz)


def normalize_range_end(dt: datetime) -> datetime:
    """
    End of the calendar day (23:59:59.999999) in the effective timezone, as an aware datetime.
    """
    tz = _effective_tz(dt)
    if dj_tz.is_naive(dt):
        local = dj_tz.make_aware(dt, tz)
    else:
        local = dt.astimezone(tz)
    day = local.date()
    return datetime.combine(day, time.max, tzinfo=tz)
