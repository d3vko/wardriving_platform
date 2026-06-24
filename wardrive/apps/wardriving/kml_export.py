"""Shared KML export resolution for HTTP views and WebSocket consumers."""

from django.db.models import Q

from apps.misc.db_views import WardrivingVendorView
from apps.wardriving.filters import LteWardrivingFilterSet, WifiWardrivingFilterSet
from apps.wardriving.models import LTEWardriving


def _exclude_default_coords():
    return ~Q(current_latitude=0, current_longitude=0)


class KmlExportError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(detail)


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
    return queryset


WIFI_KML_EXPORT = {
    "filename_tpl": "wifi_scans_{username}.kml",
    "pin_color": "ff00ffff",
    "name_fn": lambda o: o.ssid or o.mac,
    "lat_fn": lambda o: o.current_latitude,
    "lon_fn": lambda o: o.current_longitude,
    "extra_fn": lambda o: {
        "vendor": o.vendor,
        "mac": o.mac,
        "ssid": o.ssid,
        "auth_mode": o.auth_mode,
        "signal_streng": o.signal_streng,
        "device_source": o.device_source,
        "uploaded_by": o.uploaded_by,
        "type": o.type,
        "first_seen": o.first_seen,
    },
}

LTE_KML_EXPORT = {
    "filename_tpl": "lte_scans_{username}.kml",
    "pin_color": "ff0000ff",
    "name_fn": lambda o: f"{o.provider or 'LTE'} {o.cell_id}",
    "lat_fn": lambda o: o.current_latitude,
    "lon_fn": lambda o: o.current_longitude,
    "extra_fn": lambda o: {
        "provider": o.provider,
        "cell_id": o.cell_id,
        "mcc": o.mcc,
        "mnc": o.mnc,
        "lac": o.lac,
        "band": o.band,
        "rssi": o.rssi,
        "tech": o.tech,
        "device_source": o.device_source,
        "uploaded_by": o.uploaded_by,
        "first_seen": o.first_seen,
    },
}
