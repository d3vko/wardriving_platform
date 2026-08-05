"""Helpers geoespaciales: validación lat/lon → Point SRID 4326."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib.gis.geos import Point

SRID = 4326


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, TypeError, ValueError):
        return None


def is_valid_lat_lon(lat: Any, lon: Any) -> bool:
    """True si lat/lon están rangos WGS84 y no son el placeholder (0, 0)."""
    lat_f = _to_float(lat)
    lon_f = _to_float(lon)
    if lat_f is None or lon_f is None:
        return False
    if lat_f == 0.0 and lon_f == 0.0:
        return False
    return -90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0


def point_from_lat_lon(lat: Any, lon: Any) -> Point | None:
    """
    Construye un Point(lon, lat) SRID 4326, o None si inválido/cero.
    Orden GEOS/PostGIS: x=longitude, y=latitude.
    """
    if not is_valid_lat_lon(lat, lon):
        return None
    return Point(_to_float(lon), _to_float(lat), srid=SRID)


def enrich_row_location(row: dict) -> dict:
    """Añade/actualiza ``location`` en un dict de fila a partir de lat/lon."""
    row["location"] = point_from_lat_lon(
        row.get("current_latitude"),
        row.get("current_longitude"),
    )
    return row
