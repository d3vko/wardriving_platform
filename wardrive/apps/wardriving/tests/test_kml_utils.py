from types import SimpleNamespace
import threading

from django.test import SimpleTestCase
from lxml import etree

from apps.wardriving.kml_utils import (
    KmlExportCancelled,
    build_kml_bytes,
    iter_kml_chunks,
)

_SYN_LAT = 10.5000001
_SYN_LON = -70.5000001
_SYN_MAC = "02:00:00:AA:BB:CC"


class _FakeQuerySet:
    def __init__(self, items):
        self._items = items

    def iterator(self, chunk_size=2000):
        yield from self._items


class BuildKmlBytesTests(SimpleTestCase):
    def _build(self, *, name: str, extra: dict | None = None) -> bytes:
        obj = SimpleNamespace(
            name=name,
            lat=_SYN_LAT,
            lon=_SYN_LON,
            extra=extra or {},
        )
        return build_kml_bytes(
            queryset=_FakeQuerySet([obj]),
            pin_color="ff00ffff",
            name_fn=lambda o: o.name,
            lat_fn=lambda o: o.lat,
            lon_fn=lambda o: o.lon,
            extra_fn=lambda o: o.extra,
        )

    def _assert_valid_kml(self, body: bytes) -> etree._Element:
        root = etree.fromstring(body)
        self.assertEqual(root.tag, f"{{{etree.QName(root).namespace}}}kml")
        return root

    def test_plain_ssid_produces_parseable_kml(self):
        body = self._build(name="TestNetwork")
        root = self._assert_valid_kml(body)
        names = root.findall(".//{*}name")
        self.assertTrue(any(n.text == "TestNetwork" for n in names))

    def test_ssid_with_ampersand(self):
        body = self._build(
            name="Cafe & WiFi",
            extra={"ssid": "Cafe & WiFi", "mac": _SYN_MAC},
        )
        self._assert_valid_kml(body)
        self.assertIn(b"Cafe &amp; WiFi", body)

    def test_ssid_with_angle_brackets(self):
        body = self._build(name="<script>alert(1)</script>")
        self._assert_valid_kml(body)
        self.assertIn(b"&lt;script&gt;", body)

    def test_ssid_with_cdata_break_sequence(self):
        body = self._build(
            name="Broken]]>SSID",
            extra={"ssid": "Broken]]>SSID"},
        )
        self._assert_valid_kml(body)
        self.assertIn(b"Broken]]&gt;SSID", body)

    def test_ssid_with_null_control_char(self):
        body = self._build(name="Net\x00work")
        self._assert_valid_kml(body)
        self.assertNotIn(b"\x00", body)
        self.assertIn(b"Network", body)

    def test_coordinates_present(self):
        body = self._build(name="PointA")
        root = self._assert_valid_kml(body)
        coords = root.find(".//{*}coordinates")
        self.assertIsNotNone(coords)
        self.assertEqual(coords.text, f"{_SYN_LON},{_SYN_LAT},0")

    def test_cancel_stops_export(self):
        obj = SimpleNamespace(
            name="TestNetwork",
            lat=_SYN_LAT,
            lon=_SYN_LON,
            extra={},
        )
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(KmlExportCancelled):
            list(
                iter_kml_chunks(
                    queryset=_FakeQuerySet([obj]),
                    pin_color="ff00ffff",
                    name_fn=lambda o: o.name,
                    lat_fn=lambda o: o.lat,
                    lon_fn=lambda o: o.lon,
                    extra_fn=lambda o: o.extra,
                    should_cancel=cancel.is_set,
                )
            )
