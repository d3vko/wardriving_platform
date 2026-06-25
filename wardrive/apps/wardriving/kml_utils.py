import io
import re
import zipfile
from collections.abc import Callable, Iterator
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse

KML_NS = "http://www.opengis.net/kml/2.2"

# Google My Maps: unzipped KML/KMZ up to 5 MB.
GOOGLE_MAPS_KML_MAX_BYTES = 5 * 1024 * 1024
ESTIMATED_BYTES_PER_PLACEMARK = 220
LTE_ESTIMATED_BYTES_PER_PLACEMARK = 480
# Reject before generation when estimate exceeds this (header + style overhead).
MAPS_EXPORT_ESTIMATE_THRESHOLD_BYTES = int(4.75 * 1024 * 1024)

# XML 1.0 valid character ranges (strip the rest).
_INVALID_XML_CHARS = re.compile(
    r"[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD]"
)

ShouldCancel = Callable[[], bool] | None
STYLE_ID = "wardrivePin"


class KmlExportCancelled(Exception):
    """Raised when a KML export is aborted (e.g. client disconnected)."""


class ListQuerySet:
    """Minimal queryset facade over an in-memory list for KML batch exports."""

    def __init__(self, items):
        self._items = list(items)

    def iterator(self, chunk_size=2000):
        yield from self._items


def _kml_text(value) -> str:
    if value is None:
        return ""
    return _INVALID_XML_CHARS.sub("", str(value))


def _document_style_bytes(*, pin_color: str, icon_href: str) -> bytes:
    return (
        f'<Style id="{STYLE_ID}"><IconStyle>'
        f"<color>{pin_color}</color><scale>1.1</scale>"
        f"<Icon><href>{icon_href}</href></Icon>"
        f"</IconStyle></Style>\n"
    ).encode("utf-8")


def _placemark_bytes(
    *,
    name: str,
    lon: float,
    lat: float,
    description: str | None = None,
) -> bytes:
    """Placemark for Google My Maps: name → description? → styleUrl → Point."""
    safe_name = escape(_kml_text(name))
    parts = [f"<Placemark><name>{safe_name}</name>"]
    if description:
        parts.append(f"<description>{escape(_kml_text(description))}</description>")
    parts.extend(
        [
            f"<styleUrl>#{STYLE_ID}</styleUrl>",
            f"<Point><coordinates>{lon},{lat},0</coordinates></Point>",
            "</Placemark>\n",
        ]
    )
    return "".join(parts).encode("utf-8")


def _check_cancel(should_cancel: ShouldCancel) -> None:
    if should_cancel and should_cancel():
        raise KmlExportCancelled()


def iter_kml_chunks(
    *,
    queryset,
    pin_color: str,
    name_fn,
    lat_fn,
    lon_fn,
    description_fn=None,
    should_cancel: ShouldCancel = None,
) -> Iterator[bytes]:
    """Yield compact KML bytes (Google My Maps friendly)."""
    icon_href = settings.KML_ICON_HREF
    yield b'<?xml version="1.0" encoding="UTF-8"?>\n'
    yield f'<kml xmlns="{KML_NS}"><Document>\n'.encode()
    yield _document_style_bytes(pin_color=pin_color, icon_href=icon_href)

    for obj in queryset.iterator(chunk_size=2000):
        _check_cancel(should_cancel)
        lat = float(lat_fn(obj))
        lon = float(lon_fn(obj))
        description = None
        if description_fn is not None:
            raw = description_fn(obj)
            if raw:
                description = str(raw)
        yield _placemark_bytes(
            name=str(name_fn(obj)),
            lon=lon,
            lat=lat,
            description=description,
        )

    yield b"</Document></kml>\n"


def build_kml_bytes(
    *,
    queryset,
    pin_color: str,
    name_fn,
    lat_fn,
    lon_fn,
    description_fn=None,
    should_cancel: ShouldCancel = None,
) -> bytes:
    """UTF-8 KML document bytes (shared by tests and WebSocket binary frame)."""
    return b"".join(
        iter_kml_chunks(
            queryset=queryset,
            pin_color=pin_color,
            name_fn=name_fn,
            lat_fn=lat_fn,
            lon_fn=lon_fn,
            description_fn=description_fn,
            should_cancel=should_cancel,
        )
    )


def build_kml_streaming_response(
    *,
    queryset,
    filename: str,
    pin_color: str,
    name_fn,
    lat_fn,
    lon_fn,
    description_fn=None,
    should_cancel: ShouldCancel = None,
) -> StreamingHttpResponse:
    """Stream a KML download without buffering the full file in memory."""
    response = StreamingHttpResponse(
        iter_kml_chunks(
            queryset=queryset,
            pin_color=pin_color,
            name_fn=name_fn,
            lat_fn=lat_fn,
            lon_fn=lon_fn,
            description_fn=description_fn,
            should_cancel=should_cancel,
        ),
        content_type="application/vnd.google-earth.kml+xml",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def build_kml_response(
    *,
    queryset,
    filename: str,
    pin_color: str,
    name_fn,
    lat_fn,
    lon_fn,
    description_fn=None,
) -> HttpResponse:
    """Build and return a buffered KML download from a queryset."""
    body = build_kml_bytes(
        queryset=queryset,
        pin_color=pin_color,
        name_fn=name_fn,
        lat_fn=lat_fn,
        lon_fn=lon_fn,
        description_fn=description_fn,
    )
    response = HttpResponse(
        body,
        content_type="application/vnd.google-earth.kml+xml",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def build_kml_zip_bytes(
    *,
    queryset,
    chunk_size: int,
    part_filename_tpl: str,
    username: str,
    pin_color: str,
    name_fn,
    lat_fn,
    lon_fn,
    description_fn=None,
    should_cancel: ShouldCancel = None,
) -> bytes:
    """Build a ZIP of multiple KML parts, each under the Maps size budget."""
    buffer = io.BytesIO()
    part = 0
    batch: list = []
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for obj in queryset.iterator(chunk_size=2000):
            _check_cancel(should_cancel)
            batch.append(obj)
            if len(batch) >= chunk_size:
                part += 1
                kml = build_kml_bytes(
                    queryset=ListQuerySet(batch),
                    pin_color=pin_color,
                    name_fn=name_fn,
                    lat_fn=lat_fn,
                    lon_fn=lon_fn,
                    description_fn=description_fn,
                    should_cancel=should_cancel,
                )
                zf.writestr(
                    part_filename_tpl.format(username=username, part=part),
                    kml,
                )
                batch = []
        if batch:
            part += 1
            kml = build_kml_bytes(
                queryset=ListQuerySet(batch),
                pin_color=pin_color,
                name_fn=name_fn,
                lat_fn=lat_fn,
                lon_fn=lon_fn,
                description_fn=description_fn,
                should_cancel=should_cancel,
            )
            zf.writestr(
                part_filename_tpl.format(username=username, part=part),
                kml,
            )
    return buffer.getvalue()


def build_kml_zip_response(
    *,
    queryset,
    chunk_size: int,
    zip_filename: str,
    part_filename_tpl: str,
    username: str,
    pin_color: str,
    name_fn,
    lat_fn,
    lon_fn,
    description_fn=None,
    should_cancel: ShouldCancel = None,
) -> HttpResponse:
    """Return a ZIP download with one KML file per chunk."""
    body = build_kml_zip_bytes(
        queryset=queryset,
        chunk_size=chunk_size,
        part_filename_tpl=part_filename_tpl,
        username=username,
        pin_color=pin_color,
        name_fn=name_fn,
        lat_fn=lat_fn,
        lon_fn=lon_fn,
        description_fn=description_fn,
        should_cancel=should_cancel,
    )
    response = HttpResponse(body, content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{zip_filename}"'
    return response
