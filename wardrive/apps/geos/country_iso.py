"""Mapeo estático nombre de país (GADM / GHS-UCDB) → ISO 3166-1 alpha-2.

Cubre América (Norte, Centro, Sur y Caribe). Las claves están en
minúsculas y sin acentos opcionales para matching tolerante.
"""

from __future__ import annotations

import unicodedata

# Nombre canónico (como suele venir de GADM) → ISO-2
COUNTRY_NAME_TO_ISO2: dict[str, str] = {
    # North America
    "united states": "US",
    "united states of america": "US",
    "canada": "CA",
    "mexico": "MX",
    "méxico": "MX",
    # Central America
    "belize": "BZ",
    "costa rica": "CR",
    "el salvador": "SV",
    "guatemala": "GT",
    "honduras": "HN",
    "nicaragua": "NI",
    "panama": "PA",
    "panamá": "PA",
    # Caribbean
    "antigua and barbuda": "AG",
    "bahamas": "BS",
    "the bahamas": "BS",
    "barbados": "BB",
    "cuba": "CU",
    "dominica": "DM",
    "dominican republic": "DO",
    "grenada": "GD",
    "haiti": "HT",
    "haïti": "HT",
    "jamaica": "JM",
    "saint kitts and nevis": "KN",
    "saint lucia": "LC",
    "saint vincent and the grenadines": "VC",
    "trinidad and tobago": "TT",
    # Caribbean territories / dependencies commonly in GADM
    "puerto rico": "PR",
    "united states virgin islands": "VI",
    "u.s. virgin islands": "VI",
    "british virgin islands": "VG",
    "cayman islands": "KY",
    "turks and caicos islands": "TC",
    "anguilla": "AI",
    "montserrat": "MS",
    "aruba": "AW",
    "curacao": "CW",
    "curaçao": "CW",
    "sint maarten": "SX",
    "saint martin": "MF",
    "saint barthélemy": "BL",
    "saint barthelemy": "BL",
    "guadeloupe": "GP",
    "martinique": "MQ",
    "bermuda": "BM",
    "greenland": "GL",
    # South America
    "argentina": "AR",
    "bolivia": "BO",
    "brazil": "BR",
    "brasil": "BR",
    "chile": "CL",
    "colombia": "CO",
    "ecuador": "EC",
    "guyana": "GY",
    "paraguay": "PY",
    "peru": "PE",
    "perú": "PE",
    "suriname": "SR",
    "uruguay": "UY",
    "venezuela": "VE",
    "french guiana": "GF",
    "falkland islands": "FK",
    "south georgia and the south sandwich islands": "GS",
}

# ISO-2 de países/territorios del continente americano (refuerzo de filtro)
AMERICAS_ISO2: frozenset[str] = frozenset(COUNTRY_NAME_TO_ISO2.values())

# Regiones ONU (SDG) que definen América en GHS-UCDB (GC_DEV_USR_*)
AMERICAS_UN_REGIONS: frozenset[str] = frozenset(
    {
        "latin america and the caribbean",
        "northern america",
    }
)


def _normalize_name(name: str) -> str:
    text = unicodedata.normalize("NFKD", name.strip().lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


# Índice normalizado (sin acentos) → ISO-2
_NORMALIZED_TO_ISO2: dict[str, str] = {
    _normalize_name(k): v for k, v in COUNTRY_NAME_TO_ISO2.items()
}


def country_name_to_iso2(name: str | None) -> str | None:
    """Resuelve nombre de país a ISO-2, o None si no hay match."""
    if not name:
        return None
    raw = name.strip().lower()
    if raw in COUNTRY_NAME_TO_ISO2:
        return COUNTRY_NAME_TO_ISO2[raw]
    return _NORMALIZED_TO_ISO2.get(_normalize_name(name))


def is_americas_un_region(region: str | None) -> bool:
    if not region:
        return False
    return _normalize_name(region) in {
        _normalize_name(r) for r in AMERICAS_UN_REGIONS
    }
