"""Shared KML export resolution for HTTP views and WebSocket consumers."""

from collections.abc import Callable

from django.db.models import Q

from apps.misc.db_views import WardrivingVendorView
from apps.wardriving.filters import LteWardrivingFilterSet, WifiWardrivingFilterSet
from apps.wardriving.kml_utils import (
    ESTIMATED_BYTES_PER_PLACEMARK,
    LTE_ESTIMATED_BYTES_PER_PLACEMARK,
    MAPS_EXPORT_ESTIMATE_THRESHOLD_BYTES,
)
from apps.wardriving.models import LTEWardriving

WIFI_ESTIMATED_BYTES_PER_PLACEMARK = 520


def _exclude_default_coords():
    return ~Q(current_latitude=0, current_longitude=0)


class KmlExportError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(detail)


def assert_maps_export_fits(
    point_count: int,
    *,
    bytes_per_placemark: int = ESTIMATED_BYTES_PER_PLACEMARK,
) -> None:
    estimated_bytes = point_count * bytes_per_placemark
    if estimated_bytes > MAPS_EXPORT_ESTIMATE_THRESHOLD_BYTES:
        estimated_mb = estimated_bytes / (1024 * 1024)
        raise KmlExportError(
            413,
            (
                f"Este export tiene {point_count:,} puntos (~{estimated_mb:.1f} MB). "
                "Google My Maps acepta KML de hasta 5 MB. "
                "Acota el rango de fechas (first_seen_after / first_seen_before)."
            ),
        )


def plan_wifi_kml_export(point_count: int) -> tuple[str, int]:
    """
    Decide single .kml vs multi-part ZIP for Google My Maps (5 MB limit).

    Returns (mode, chunk_size) where mode is "single" or "zip".
  """
    estimated_bytes = point_count * WIFI_ESTIMATED_BYTES_PER_PLACEMARK
    if estimated_bytes <= MAPS_EXPORT_ESTIMATE_THRESHOLD_BYTES:
        return "single", point_count
    chunk_size = max(
        1,
        MAPS_EXPORT_ESTIMATE_THRESHOLD_BYTES // WIFI_ESTIMATED_BYTES_PER_PLACEMARK,
    )
    return "zip", chunk_size


def _require_date_bounds(params: dict) -> None:
    if not params.get("first_seen_after") or not params.get("first_seen_before"):
        raise KmlExportError(
            400,
            "KML export requires both first_seen_after and first_seen_before "
            "(ISO 8601) with a bounded date range.",
        )


def _filtered_queryset(filterset_class, *, base_qs, params: dict):
    filterset = filterset_class(data=params, queryset=base_qs)
    if not filterset.is_valid():
        raise KmlExportError(400, str(filterset.errors))
    return filterset.qs


def resolve_wifi_kml_queryset(user, params: dict):
    _require_date_bounds(params)
    base = WardrivingVendorView.objects.filter(
        uploaded_by=user.username
    ).order_by("-first_seen")
    queryset = _filtered_queryset(
        WifiWardrivingFilterSet,
        base_qs=base,
        params=params,
    )
    if not queryset.exists():
        raise KmlExportError(
            404,
            "No WiFi samples to export for your user in this date range.",
        )
    return queryset


def resolve_lte_kml_queryset(user, params: dict):
    _require_date_bounds(params)
    base = LTEWardriving.objects.filter(
        _exclude_default_coords(),
        uploaded_by=user.username,
    ).order_by("-first_seen")
    queryset = _filtered_queryset(
        LteWardrivingFilterSet,
        base_qs=base,
        params=params,
    )
    if not queryset.exists():
        raise KmlExportError(
            404,
            "No LTE samples to export for your user in this date range.",
        )
    assert_maps_export_fits(
        queryset.count(),
        bytes_per_placemark=LTE_ESTIMATED_BYTES_PER_PLACEMARK,
    )
    return queryset


def _kml_field(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _lines_description(
    obj,
    field_specs: list[tuple[str, Callable]],
) -> str:
    lines: list[str] = []
    for label, getter in field_specs:
        raw = getter(obj)
        if raw is None:
            continue
        text = _kml_field(raw) if not isinstance(raw, (int, float)) else str(raw)
        if text == "":
            continue
        lines.append(f"{label}: {text}")
    return "\n".join(lines)


def _nonzero_decimal(value) -> str | None:
    if value is None:
        return None
    try:
        if float(value) == 0:
            return None
    except (TypeError, ValueError):
        return None
    return str(value)


def _wifi_placemark_name(obj) -> str:
    if obj.ssid:
        return f"{obj.ssid} ({obj.mac})"
    return obj.mac


def _wifi_placemark_description(obj) -> str:
    return _lines_description(
        obj,
        [
            ("SSID", lambda o: _kml_field(o.ssid) or None),
            ("MAC", lambda o: o.mac),
            ("Vendor", lambda o: _kml_field(o.vendor) or None),
            ("Registry", lambda o: _kml_field(getattr(o, "registry", "")) or None),
            ("Source", lambda o: _kml_field(getattr(o, "source", "")) or None),
            ("Auth", lambda o: _kml_field(o.auth_mode) or None),
            ("Canal", lambda o: getattr(o, "channel", None)),
            ("RSSI", lambda o: f"{o.rssi} dBm" if o.rssi is not None else None),
            ("Señal", lambda o: _kml_field(getattr(o, "signal_streng", "")) or None),
            ("Tipo", lambda o: _kml_field(o.type) or None),
            ("Dispositivo", lambda o: _kml_field(o.device_source) or None),
            (
                "Altitud",
                lambda o: (
                    f"{_nonzero_decimal(o.altitude_meters)} m"
                    if _nonzero_decimal(o.altitude_meters)
                    else None
                ),
            ),
            (
                "Precisión GPS",
                lambda o: (
                    f"{_nonzero_decimal(o.accuracy_meters)} m"
                    if _nonzero_decimal(o.accuracy_meters)
                    else None
                ),
            ),
        ],
    )


def _lte_placemark_name(obj) -> str:
    provider = _kml_field(obj.provider) or "LTE"
    pci = getattr(obj, "pci", None)
    if pci:
        return f"{provider} | Cell {obj.cell_id} (PCI {pci})"
    return f"{provider} | Cell {obj.cell_id}"


def _lte_placemark_description(obj) -> str:
    return _lines_description(
        obj,
        [
            ("Operador", lambda o: _kml_field(o.provider) or None),
            ("PLMN (MCC-MNC)", lambda o: f"{o.mcc}-{o.mnc}"),
            ("LAC", lambda o: o.lac),
            ("Cell ID (CGI)", lambda o: o.cell_id),
            (
                "eNodeB",
                lambda o: (
                    f"{o.enodeb_id}  Sector: {o.sector_id}"
                    if getattr(o, "enodeb_id", None)
                    else None
                ),
            ),
            ("PCI", lambda o: getattr(o, "pci", None) or None),
            ("Banda", lambda o: _kml_field(getattr(o, "band", "")) or None),
            ("EARFCN", lambda o: getattr(o, "earfcn", None) or None),
            (
                "DL",
                lambda o: (
                    f"{_nonzero_decimal(o.dl_freq_mhz)} MHz"
                    if _nonzero_decimal(o.dl_freq_mhz)
                    else None
                ),
            ),
            (
                "UL",
                lambda o: (
                    f"{_nonzero_decimal(o.ul_freq_mhz)} MHz"
                    if _nonzero_decimal(o.ul_freq_mhz)
                    else None
                ),
            ),
            ("Tecnología", lambda o: _kml_field(getattr(o, "tech", "")) or None),
            (
                "Tipo de celda",
                lambda o: _kml_field(getattr(o, "cell_type", "")) or None,
            ),
            ("RSSI", lambda o: f"{o.rssi} dBm"),
            ("RSRP", lambda o: getattr(o, "rsrp", None)),
            ("RSRQ", lambda o: getattr(o, "rsrq", None)),
            ("SINR", lambda o: getattr(o, "sinr", None)),
            ("Dispositivo", lambda o: _kml_field(o.device_source) or None),
        ],
    )


WIFI_KML_EXPORT = {
    "filename_tpl": "wifi_scans_{username}.kml",
    "zip_filename_tpl": "wifi_scans_{username}.zip",
    "part_filename_tpl": "wifi_scans_{username}_part{part:03d}.kml",
    "pin_color": "ff00ffff",
    "name_fn": _wifi_placemark_name,
    "description_fn": _wifi_placemark_description,
    "lat_fn": lambda o: o.current_latitude,
    "lon_fn": lambda o: o.current_longitude,
}

LTE_KML_EXPORT = {
    "filename_tpl": "lte_scans_{username}.kml",
    "pin_color": "ff0000ff",
    "name_fn": _lte_placemark_name,
    "description_fn": _lte_placemark_description,
    "lat_fn": lambda o: o.current_latitude,
    "lon_fn": lambda o: o.current_longitude,
}
