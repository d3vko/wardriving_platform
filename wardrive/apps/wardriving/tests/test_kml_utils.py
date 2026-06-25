from types import SimpleNamespace
import io
import threading
import zipfile

from django.test import SimpleTestCase
from lxml import etree

from apps.wardriving.kml_export import (
    KmlExportError,
    WIFI_ESTIMATED_BYTES_PER_PLACEMARK,
    _lte_placemark_description,
    _lte_placemark_name,
    _wifi_placemark_description,
    _wifi_placemark_name,
    assert_maps_export_fits,
    plan_wifi_kml_export,
)
from apps.wardriving.kml_utils import (
    GOOGLE_MAPS_KML_MAX_BYTES,
    KML_NS,
    KmlExportCancelled,
    MAPS_EXPORT_ESTIMATE_THRESHOLD_BYTES,
    build_kml_bytes,
    build_kml_zip_bytes,
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
            uploaded_by="testuser",
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


def _wifi_obj(i: int = 0):
    return SimpleNamespace(
        ssid=f"TestNet-{i}",
        mac=_SYN_MAC,
        vendor="Synthetic Vendor",
        registry="",
        source="test",
        auth_mode="WPA2",
        channel=6,
        rssi=-65,
        signal_streng="Good",
        type="wifi",
        device_source="test-device",
        uploaded_by="testuser",
        first_seen="2025-01-01T12:00:00Z",
        altitude_meters="10.5",
        accuracy_meters="5.0",
        current_latitude=_SYN_LAT + i * 0.0001,
        current_longitude=_SYN_LON + i * 0.0001,
    )


class WifiKmlDescriptionTests(SimpleTestCase):
    def test_wifi_placemark_includes_full_metadata(self):
        obj = _wifi_obj()
        body = build_kml_bytes(
            queryset=_FakeQuerySet([obj]),
            pin_color="ff00ffff",
            name_fn=_wifi_placemark_name,
            lat_fn=lambda o: o.current_latitude,
            lon_fn=lambda o: o.current_longitude,
            description_fn=_wifi_placemark_description,
        )
        root = etree.fromstring(body)
        placemark = root.find(f".//{{{KML_NS}}}Placemark")
        child_names = [etree.QName(child).localname for child in placemark]
        self.assertEqual(child_names, ["name", "description", "styleUrl", "Point"])
        description = placemark.find(f"{{{KML_NS}}}description")
        self.assertIsNotNone(description)
        text = description.text or ""
        self.assertIn("Synthetic Vendor", text)
        self.assertIn(_SYN_MAC, text)
        self.assertIn("WPA2", text)
        self.assertIn("Good", text)
        self.assertIn("2025-01-01T12:00:00Z", text)

    def test_wifi_description_special_chars_escaped(self):
        obj = _wifi_obj()
        obj.ssid = "Cafe & WiFi <test>"
        body = build_kml_bytes(
            queryset=_FakeQuerySet([obj]),
            pin_color="ff00ffff",
            name_fn=_wifi_placemark_name,
            lat_fn=lambda o: o.current_latitude,
            lon_fn=lambda o: o.current_longitude,
            description_fn=_wifi_placemark_description,
        )
        etree.fromstring(body)
        self.assertIn(b"Cafe &amp; WiFi", body)


class PlanWifiKmlExportTests(SimpleTestCase):
    def test_small_export_returns_single(self):
        max_single = MAPS_EXPORT_ESTIMATE_THRESHOLD_BYTES // WIFI_ESTIMATED_BYTES_PER_PLACEMARK
        mode, _ = plan_wifi_kml_export(max_single)
        self.assertEqual(mode, "single")

    def test_large_export_returns_zip_with_chunk_size(self):
        max_single = MAPS_EXPORT_ESTIMATE_THRESHOLD_BYTES // WIFI_ESTIMATED_BYTES_PER_PLACEMARK
        mode, chunk_size = plan_wifi_kml_export(max_single + 1)
        self.assertEqual(mode, "zip")
        self.assertEqual(
            chunk_size,
            MAPS_EXPORT_ESTIMATE_THRESHOLD_BYTES // WIFI_ESTIMATED_BYTES_PER_PLACEMARK,
        )


class BuildKmlZipTests(SimpleTestCase):
    def test_zip_splits_into_parseable_parts(self):
        items = [_wifi_obj(i) for i in range(7)]
        body = build_kml_zip_bytes(
            queryset=_FakeQuerySet(items),
            chunk_size=3,
            part_filename_tpl="wifi_scans_{username}_part{part:03d}.kml",
            username="testuser",
            pin_color="ff00ffff",
            name_fn=_wifi_placemark_name,
            lat_fn=lambda o: o.current_latitude,
            lon_fn=lambda o: o.current_longitude,
            description_fn=_wifi_placemark_description,
        )
        with zipfile.ZipFile(io.BytesIO(body)) as zf:
            names = sorted(zf.namelist())
            self.assertEqual(len(names), 3)
            self.assertEqual(names[0], "wifi_scans_testuser_part001.kml")
            total_placemarks = 0
            for name in names:
                kml = zf.read(name)
                root = etree.fromstring(kml)
                total_placemarks += len(
                    root.findall(f".//{{{KML_NS}}}Placemark")
                )
            self.assertEqual(total_placemarks, 7)
