"""
Shared canonical pipeline for WiGLE CSV variants.

Provides: dialect detection, header alias resolution, canonical row schema,
type coercion, and persistence — all independent of version strings.
"""

from .aliases import HEADER_ALIASES, resolve_headers
from .detect import detect_dialect
from .persist import persist_canonical_rows
from .sanitizers import sanitize_security
from .schema import CanonicalRow, REQUIRED_FIELDS, coerce_row

__all__ = [
    "HEADER_ALIASES",
    "resolve_headers",
    "detect_dialect",
    "persist_canonical_rows",
    "sanitize_security",
    "CanonicalRow",
    "REQUIRED_FIELDS",
    "coerce_row",
]
