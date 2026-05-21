"""
Sanitizers for WiGLE / Marauder security/auth-mode values.

WiGLE and several Marauder forks encode security capabilities in bracket notation:
    [WPA2-PSK-CCMP-128][RSN-PSK-CCMP-128][ESS]
    [WPA2-EAP/SHA1-CCMP-128][RSN-...][ESS]
    [ESS]

Marauder log parsers already strip the brackets via regex capture groups, so
values that arrive without brackets are passed through unchanged.
"""

from __future__ import annotations

import re

_BRACKET_RE = re.compile(r"\[([^\]]+)\]")


def sanitize_security(raw: str | None) -> str | None:
    """
    Normalize a security/auth-mode string to its primary token, without brackets.

    Rules:
    - None or empty string        → None
    - "[TOKEN1][TOKEN2]…"         → first token (inner text of first bracket pair)
    - "[WPA2-EAP/SHA1-CCMP]…"    → first token split at "/" → "WPA2-EAP"
    - "WPA2_PSK" (no brackets)   → "WPA2_PSK"  (passthrough — log parser already stripped them)
    - whitespace-only             → None
    """
    if not raw:
        return None
    if not isinstance(raw, str):
        raw = str(raw)
    raw = raw.strip()
    if not raw:
        return None

    tokens = _BRACKET_RE.findall(raw)
    if tokens:
        first = tokens[0].strip()
        if "/" in first:
            first = first.split("/")[0]
        return first or None

    # String starts with '[' but no extractable content (e.g. "[]") → malformed
    if raw.startswith("["):
        return None

    # No brackets at all: already clean (Marauder log format — passthrough)
    return raw or None
