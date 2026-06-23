from io import BytesIO
from xml.sax.saxutils import escape

import simplekml  # type: ignore[import-not-found]

from django.http import HttpResponse
from django.conf import settings


def _build_description(rows: list[tuple[str, str]]) -> str:
    table_rows = "".join(
        f"<tr><td><b>{escape(str(k))}</b></td><td>{escape(str(v))}</td></tr>"
        for k, v in rows
    )
    return (
        "<![CDATA[<div style='font-family:Arial;font-size:13px;'>"
        "<table border='1' cellpadding='4' cellspacing='0' style='border-collapse:collapse;'>"
        f"{table_rows}"
        "</table></div>]]>"
    )


def build_kml_bytes(
    *,
    queryset,
    pin_color: str,
    name_fn,
    lat_fn,
    lon_fn,
    extra_fn,
) -> bytes:
    """UTF-8 KML document bytes (shared by HTTP response and WebSocket binary frame)."""
    kml = simplekml.Kml()
    icon_href = settings.KML_ICON_HREF

    for obj in queryset.iterator(chunk_size=2000):
        lat = float(lat_fn(obj))
        lon = float(lon_fn(obj))
        extra_data = extra_fn(obj) or {}
        name = str(name_fn(obj))

        point = kml.newpoint(name=name, coords=[(lon, lat)])
        point.style.iconstyle.icon.href = icon_href
        point.style.iconstyle.color = pin_color
        point.style.iconstyle.scale = 1.1

        if extra_data:
            point.description = _build_description(
                [(str(k), "" if v is None else str(v)) for k, v in extra_data.items()]
            )
            ext = simplekml.ExtendedData()
            for k, v in extra_data.items():
                ext.newdata(name=str(k), value="" if v is None else str(v))
            point.extendeddata = ext

    buffer = BytesIO()
    buffer.write(kml.kml().encode("utf-8"))
    return buffer.getvalue()


def build_kml_response(
    *,
    queryset,
    filename: str,
    pin_color: str,
    name_fn,
    lat_fn,
    lon_fn,
    extra_fn,
) -> HttpResponse:
    """
    Build and return a KML download from a queryset.

    Each callable receives `obj` and returns:
    - name_fn -> str for the placemark name
    - lat_fn/lon_fn -> coordinates
    - extra_fn -> dict of metadata for table/extended data
    """
    body = build_kml_bytes(
        queryset=queryset,
        pin_color=pin_color,
        name_fn=name_fn,
        lat_fn=lat_fn,
        lon_fn=lon_fn,
        extra_fn=extra_fn,
    )
    response = HttpResponse(
        body,
        content_type="application/vnd.google-earth.kml+xml",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
