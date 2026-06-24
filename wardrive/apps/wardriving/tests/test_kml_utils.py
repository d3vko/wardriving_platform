from types import SimpleNamespace
import threading

from django.test import SimpleTestCase
from lxml import etree

from apps.wardriving.kml_export import (
    KmlExportError,
    _lte_placemark_description,
    _lte_placemark_name,
    assert_maps_export_fits,
)
from apps.wardriving.kml_utils import (
    GOOGLE_MAPS_KML_MAX_BYTES,
    KML_NS,
    KmlExportCancelled,
    MAPS_EXPORT_ESTIMATE_THRESHOLD_BYTES,
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
    def _build(self, *, name: str) -> bytes:
        obj = SimpleNamespace(
            name=name,
            lat=_SYN_LAT,
            lon=_SYN_LON,
        )
        return build_kml_bytes(
            queryset=_FakeQuerySet([obj]),
            pin_color="ff00ffff",
            name_fn=lambda o: o.name,
            lat_fn=lambda o: o.lat,
            lon_fn=lambda o: o.lon,
        )

    def _assert_valid_kml(self, body: bytes) -> etree._Element:
        root = etree.fromstring(body)
        self.assertEqual(root.tag, f"{{{KML_NS}}}kml")
        return root

    def test_plain_ssid_produces_parseable_kml(self):
        body = self._build(name="TestNetwork")
        root = self._assert_valid_kml(body)
        names = root.findall(f".//{{{KML_NS}}}name")
        self.assertTrue(any(n.text == "TestNetwork" for n in names))

    def test_ssid_with_ampersand(self):
        body = self._build(name="Cafe & WiFi")
        self._assert_valid_kml(body)
        self.assertIn(b"Cafe &amp; WiFi", body)

    def test_ssid_with_angle_brackets(self):
        body = self._build(name="<script>alert(1)</script>")
        self._assert_valid_kml(body)
        self.assertIn(b"&lt;script&gt;", body)

    def test_ssid_with_cdata_break_sequence(self):
        body = self._build(name="Broken]]>SSID")
        self._assert_valid_kml(body)
        self.assertIn(b"Broken]]&gt;SSID", body)

    def test_ssid_with_null_control_char(self):
        body = self._build(name="Net\x00work")
        self._assert_valid_kml(body)
        self.assertNotIn(b"\x00", body)
        self.assertIn(b"Network", body)

    def test_placemark_element_order_for_google_maps(self):
        body = self._build(name="TestNetwork")
        root = etree.fromstring(body)
        placemark = root.find(f".//{{{KML_NS}}}Placemark")
        self.assertIsNotNone(placemark)
        child_names = [etree.QName(child).localname for child in placemark]
        self.assertEqual(child_names, ["name", "styleUrl", "Point"])
        self.assertIsNone(root.find(f".//{{{KML_NS}}}description"))
        self.assertIsNone(root.find(f".//{{{KML_NS}}}ExtendedData"))

    def test_coordinates_present(self):
        body = self._build(name="PointA")
        root = self._assert_valid_kml(body)
        coords = root.find(f".//{{{KML_NS}}}coordinates")
        self.assertIsNotNone(coords)
        self.assertEqual(coords.text, f"{_SYN_LON},{_SYN_LAT},0")

    def test_cancel_stops_export(self):
        obj = SimpleNamespace(name="TestNetwork", lat=_SYN_LAT, lon=_SYN_LON)
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
                    should_cancel=cancel.is_set,
                )
            )

    def test_thousand_placemarks_under_maps_limit(self):
        items = [
            SimpleNamespace(
                name=f"Net-{i}",
                lat=_SYN_LAT + i * 0.0001,
                lon=_SYN_LON + i * 0.0001,
            )
            for i in range(1000)
        ]
        body = build_kml_bytes(
            queryset=_FakeQuerySet(items),
            pin_color="ff00ffff",
            name_fn=lambda o: o.name,
            lat_fn=lambda o: o.lat,
            lon_fn=lambda o: o.lon,
        )
        self.assertLess(len(body), GOOGLE_MAPS_KML_MAX_BYTES)
        self._assert_valid_kml(body)


class AssertMapsExportFitsTests(SimpleTestCase):
    def test_rejects_export_over_threshold(self):
        point_count = (MAPS_EXPORT_ESTIMATE_THRESHOLD_BYTES // 220) + 1
        with self.assertRaises(KmlExportError) as ctx:
            assert_maps_export_fits(point_count)
        self.assertEqual(ctx.exception.status, 413)
        self.assertIn("Google My Maps", ctx.exception.detail)

    def test_allows_export_under_threshold(self):
        assert_maps_export_fits(1000)


class LteKmlDescriptionTests(SimpleTestCase):
    def test_lte_placemark_includes_antenna_metadata(self):
        obj = SimpleNamespace(
            provider="TestCarrier",
            mcc=310,
            mnc=410,
            lac=10001,
            cell_id=25600021,
            enodeb_id=100000,
            sector_id=21,
            pci=123,
            band="B3",
            earfcn=1300,
            dl_freq_mhz="1800.0",
            ul_freq_mhz="1750.0",
            tech="LTE",
            cell_type="serving",
            rssi=-85,
            rsrp=-95,
            rsrq=-10,
            sinr=12,
            device_source="test-device",
            first_seen="2025-01-01T12:00:00Z",
            lat=_SYN_LAT,
            lon=_SYN_LON,
        )
        body = build_kml_bytes(
            queryset=_FakeQuerySet([obj]),
            pin_color="ff0000ff",
            name_fn=_lte_placemark_name,
            lat_fn=lambda o: o.lat,
            lon_fn=lambda o: o.lon,
            description_fn=_lte_placemark_description,
        )
        root = etree.fromstring(body)
        placemark = root.find(f".//{{{KML_NS}}}Placemark")
        child_names = [etree.QName(child).localname for child in placemark]
        self.assertEqual(child_names, ["name", "description", "styleUrl", "Point"])
        description = placemark.find(f"{{{KML_NS}}}description")
        self.assertIsNotNone(description)
        text = description.text or ""
        self.assertIn("TestCarrier", text)
        self.assertIn("310-410", text)
        self.assertIn("PCI: 123", text)
        self.assertIn("eNodeB: 100000", text)
        self.assertIn("RSRP: -95", text)
        self.assertIn("EARFCN: 1300", text)
