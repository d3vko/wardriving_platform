import re
from collections.abc import Callable, Iterator
from xml.sax.saxutils import escape

from lxml import etree

from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse

KML_NS = "http://www.opengis.net/kml/2.2"
KML_NSMAP = {None: KML_NS}

# XML 1.0 valid character ranges (strip the rest).
_INVALID_XML_CHARS = re.compile(
    r"[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD]"
)

ShouldCancel = Callable[[], bool] | None


class KmlExportCancelled(Exception):
    """Raised when a KML export is aborted (e.g. client disconnected)."""


def _kml_text(value) -> str:
    if value is None:
        return ""
    return _INVALID_XML_CHARS.sub("", str(value))


def _cdata_safe(text: str) -> str:
    return text.replace("]]>", "]]]]><![CDATA[>")


def _build_description(rows: list[tuple[str, str]]) -> str:
    table_rows = "".join(
        f"<tr><td><b>{escape(_kml_text(k))}</b></td>"
        f"<td>{escape(_kml_text(v))}</td></tr>"
        for k, v in rows
    )
    return _cdata_safe(
        "<div style='font-family:Arial;font-size:13px;'>"
        "<table border='1' cellpadding='4' cellspacing='0' "
        "style='border-collapse:collapse;'>"
        f"{table_rows}"
        "</table></div>"
    )


def _document_style_element(
    *,
    style_id: str,
    pin_color: str,
    icon_href: str,
) -> etree.Element:
    style = etree.Element("Style", nsmap=KML_NSMAP, id=style_id)
    icon_style = etree.SubElement(style, "IconStyle")
    color_el = etree.SubElement(icon_style, "color")
    color_el.text = pin_color
    scale_el = etree.SubElement(icon_style, "scale")
    scale_el.text = "1.1"
    icon = etree.SubElement(icon_style, "Icon")
    href_el = etree.SubElement(icon, "href")
    href_el.text = icon_href
    return style


def _placemark_element(
    *,
    name: str,
    lon: float,
    lat: float,
    style_id: str,
    extra_data: dict,
) -> etree.Element:
    """Build a Placemark; element order matches KML 2.2 / Google Maps expectations."""
    placemark = etree.Element("Placemark", nsmap=KML_NSMAP)

    name_el = etree.SubElement(placemark, "name")
    name_el.text = _kml_text(name)

    if extra_data:
        description = etree.SubElement(placemark, "description")
        description.text = etree.CDATA(
            _build_description(
                [
                    (str(k), "" if v is None else str(v))
                    for k, v in extra_data.items()
                ]
            )
        )

    style_url = etree.SubElement(placemark, "styleUrl")
    style_url.text = f"#{style_id}"

    if extra_data:
        extended = etree.SubElement(placemark, "ExtendedData")
        for key, value in extra_data.items():
            data = etree.SubElement(extended, "Data", name=_kml_text(key))
            value_el = etree.SubElement(data, "value")
            value_el.text = _kml_text("" if value is None else value)

    point = etree.SubElement(placemark, "Point")
    coordinates = etree.SubElement(point, "coordinates")
    coordinates.text = f"{lon},{lat},0"

    return placemark


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
    extra_fn,
    should_cancel: ShouldCancel = None,
) -> Iterator[bytes]:
    """Yield KML bytes incrementally (keeps HTTP/WS connections alive during long exports)."""
    icon_href = settings.KML_ICON_HREF
    style_id = "wardrivePin"
    yield b'<?xml version="1.0" encoding="UTF-8"?>\n'
    yield f'<kml xmlns="{KML_NS}"><Document>\n'.encode()
    yield etree.tostring(
        _document_style_element(
            style_id=style_id,
            pin_color=pin_color,
            icon_href=icon_href,
        ),
        encoding="utf-8",
    )

    for index, obj in enumerate(queryset.iterator(chunk_size=2000), start=1):
        _check_cancel(should_cancel)
        lat = float(lat_fn(obj))
        lon = float(lon_fn(obj))
        extra_data = extra_fn(obj) or {}
        placemark = _placemark_element(
            name=str(name_fn(obj)),
            lon=lon,
            lat=lat,
            style_id=style_id,
            extra_data=extra_data,
        )
        yield etree.tostring(placemark, encoding="utf-8")
        placemark.clear()

    yield b"</Document></kml>\n"


def build_kml_bytes(
    *,
    queryset,
    pin_color: str,
    name_fn,
    lat_fn,
    lon_fn,
    extra_fn,
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
            extra_fn=extra_fn,
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
    extra_fn,
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
            extra_fn=extra_fn,
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
    extra_fn,
) -> HttpResponse:
    """
    Build and return a buffered KML download from a queryset.

    Prefer build_kml_streaming_response for large exports over HTTP.
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
