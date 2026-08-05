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
    # Mojibake UTF-8→Latin-1 que aparece en OGR/GPKG mal etiquetado
    "mã©xico": "MX",
    "mãxico": "MX",
    "mÃ©xico": "MX",
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

# ISO-3 → ISO-2 (América + territorios), p. ej. shapeGroup de geoBoundaries CGAZ
ISO3_TO_ISO2: dict[str, str] = {
    "USA": "US",
    "CAN": "CA",
    "MEX": "MX",
    "BLZ": "BZ",
    "CRI": "CR",
    "SLV": "SV",
    "GTM": "GT",
    "HND": "HN",
    "NIC": "NI",
    "PAN": "PA",
    "ATG": "AG",
    "BHS": "BS",
    "BRB": "BB",
    "CUB": "CU",
    "DMA": "DM",
    "DOM": "DO",
    "GRD": "GD",
    "HTI": "HT",
    "JAM": "JM",
    "KNA": "KN",
    "LCA": "LC",
    "VCT": "VC",
    "TTO": "TT",
    "PRI": "PR",
    "VIR": "VI",
    "VGB": "VG",
    "CYM": "KY",
    "TCA": "TC",
    "AIA": "AI",
    "MSR": "MS",
    "ABW": "AW",
    "CUW": "CW",
    "SXM": "SX",
    "MAF": "MF",
    "BLM": "BL",
    "GLP": "GP",
    "MTQ": "MQ",
    "BMU": "BM",
    "GRL": "GL",
    "ARG": "AR",
    "BOL": "BO",
    "BRA": "BR",
    "CHL": "CL",
    "COL": "CO",
    "ECU": "EC",
    "GUY": "GY",
    "PRY": "PY",
    "PER": "PE",
    "SUR": "SR",
    "URY": "UY",
    "VEN": "VE",
    "GUF": "GF",
    "FLK": "FK",
    "SGS": "GS",
}

AMERICAS_ISO3: frozenset[str] = frozenset(ISO3_TO_ISO2.keys())

ISO2_TO_COUNTRY_NAME: dict[str, str] = {
    "US": "United States",
    "CA": "Canada",
    "MX": "Mexico",
    "BZ": "Belize",
    "CR": "Costa Rica",
    "SV": "El Salvador",
    "GT": "Guatemala",
    "HN": "Honduras",
    "NI": "Nicaragua",
    "PA": "Panama",
    "AG": "Antigua and Barbuda",
    "BS": "Bahamas",
    "BB": "Barbados",
    "CU": "Cuba",
    "DM": "Dominica",
    "DO": "Dominican Republic",
    "GD": "Grenada",
    "HT": "Haiti",
    "JM": "Jamaica",
    "KN": "Saint Kitts and Nevis",
    "LC": "Saint Lucia",
    "VC": "Saint Vincent and the Grenadines",
    "TT": "Trinidad and Tobago",
    "PR": "Puerto Rico",
    "VI": "United States Virgin Islands",
    "VG": "British Virgin Islands",
    "KY": "Cayman Islands",
    "TC": "Turks and Caicos Islands",
    "AI": "Anguilla",
    "MS": "Montserrat",
    "AW": "Aruba",
    "CW": "Curacao",
    "SX": "Sint Maarten",
    "MF": "Saint Martin",
    "BL": "Saint Barthelemy",
    "GP": "Guadeloupe",
    "MQ": "Martinique",
    "BM": "Bermuda",
    "GL": "Greenland",
    "AR": "Argentina",
    "BO": "Bolivia",
    "BR": "Brazil",
    "CL": "Chile",
    "CO": "Colombia",
    "EC": "Ecuador",
    "GY": "Guyana",
    "PY": "Paraguay",
    "PE": "Peru",
    "SR": "Suriname",
    "UY": "Uruguay",
    "VE": "Venezuela",
    "GF": "French Guiana",
    "FK": "Falkland Islands",
    "GS": "South Georgia and the South Sandwich Islands",
}


def iso3_to_iso2(code: str | None) -> str | None:
    if not code:
        return None
    return ISO3_TO_ISO2.get(code.strip().upper())


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


def _fix_mojibake(text: str) -> str:
    """Corrige UTF-8 leído como Latin-1 (p. ej. 'MÃ©xico' → 'México')."""
    if "Ã" not in text and "Â" not in text:
        return text
    try:
        fixed = text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text
    if fixed != text and ("Ã" not in fixed and "Â" not in fixed):
        return fixed
    return text


def country_name_to_iso2(name: str | None) -> str | None:
    """Resuelve nombre de país a ISO-2, o None si no hay match."""
    if not name:
        return None
    candidates = [name.strip(), _fix_mojibake(name.strip())]
    for cand in candidates:
        raw = cand.lower()
        if raw in COUNTRY_NAME_TO_ISO2:
            return COUNTRY_NAME_TO_ISO2[raw]
        mapped = _NORMALIZED_TO_ISO2.get(_normalize_name(cand))
        if mapped:
            return mapped
    return None


def is_americas_un_region(region: str | None) -> bool:
    if not region:
        return False
    return _normalize_name(region) in {
        _normalize_name(r) for r in AMERICAS_UN_REGIONS
    }
