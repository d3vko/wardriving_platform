"""Shared KML export resolution for HTTP views and WebSocket consumers."""

from django.db.models import Q

from apps.misc.db_views import WardrivingVendorView
from apps.wardriving.filters import LteWardrivingFilterSet, WifiWardrivingFilterSet
from apps.wardriving.kml_utils import (
    ESTIMATED_BYTES_PER_PLACEMARK,
    LTE_ESTIMATED_BYTES_PER_PLACEMARK,
    MAPS_EXPORT_ESTIMATE_THRESHOLD_BYTES,
)
from apps.wardriving.models import LTEWardriving


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
    assert_maps_export_fits(queryset.count())
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


def _wifi_placemark_name(obj) -> str:
    if obj.ssid:
        return f"{obj.ssid} ({obj.mac})"
    return obj.mac


def _lte_placemark_name(obj) -> str:
    provider = _kml_field(obj.provider) or "LTE"
    pci = getattr(obj, "pci", None)
    if pci:
        return f"{provider} | Cell {obj.cell_id} (PCI {pci})"
    return f"{provider} | Cell {obj.cell_id}"


def _kml_field(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _lte_placemark_description(obj) -> str:
    """Plain-text antenna/cell metadata for Google Maps popups."""
    lines: list[str] = []

    provider = _kml_field(obj.provider)
    if provider:
        lines.append(f"Operador: {provider}")

    lines.append(f"PLMN (MCC-MNC): {obj.mcc}-{obj.mnc}")
    lines.append(f"LAC: {obj.lac}")
    lines.append(f"Cell ID (CGI): {obj.cell_id}")

    enodeb = getattr(obj, "enodeb_id", None)
    sector = getattr(obj, "sector_id", None)
    if enodeb:
        lines.append(f"eNodeB: {enodeb}  Sector: {sector}")

    pci = getattr(obj, "pci", None)
    if pci:
        lines.append(f"PCI: {pci}")

    band = _kml_field(getattr(obj, "band", ""))
    if band:
        lines.append(f"Banda: {band}")

    earfcn = getattr(obj, "earfcn", None)
    if earfcn:
        lines.append(f"EARFCN: {earfcn}")

    dl = getattr(obj, "dl_freq_mhz", None)
    ul = getattr(obj, "ul_freq_mhz", None)
    if dl and float(dl) != 0:
        lines.append(f"DL: {dl} MHz")
    if ul and float(ul) != 0:
        lines.append(f"UL: {ul} MHz")

    tech = _kml_field(getattr(obj, "tech", ""))
    if tech:
        lines.append(f"Tecnología: {tech}")

    cell_type = _kml_field(getattr(obj, "cell_type", ""))
    if cell_type:
        lines.append(f"Tipo de celda: {cell_type}")

    lines.append(f"RSSI: {obj.rssi} dBm")

    rsrp = getattr(obj, "rsrp", None)
    rsrq = getattr(obj, "rsrq", None)
    sinr = getattr(obj, "sinr", None)
    if rsrp is not None:
        lines.append(f"RSRP: {rsrp} dBm")
    if rsrq is not None:
        lines.append(f"RSRQ: {rsrq} dB")
    if sinr is not None:
        lines.append(f"SINR: {sinr} dB")

    device = _kml_field(getattr(obj, "device_source", ""))
    if device:
        lines.append(f"Dispositivo: {device}")

    first_seen = getattr(obj, "first_seen", None)
    if first_seen:
        lines.append(f"first_seen: {first_seen}")

    return "\n".join(lines)


WIFI_KML_EXPORT = {
    "filename_tpl": "wifi_scans_{username}.kml",
    "pin_color": "ff00ffff",
    "name_fn": _wifi_placemark_name,
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
