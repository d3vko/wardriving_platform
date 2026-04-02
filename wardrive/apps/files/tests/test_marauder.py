"""Unit tests for Flipper/Marauder log parsing (apps.process.marauder)."""

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.process.marauder import (
    _detect_flipper_marauder_log_style,
    _parse_marauder_ble_device_malformed,
    _parse_marauder_line_classic,
    _parse_marauder_wifi_line,
    process_format_flipper_marauder_v2,
)


class DetectFlipperMarauderStyleTests(SimpleTestCase):
    def test_header_startingwardrive_forces_classic(self):
        lines = [
            "# log\n",
            "StartingWardrive. Stop with stopscan\n",
            "1 | aa:bb:cc:dd:ee:ff,x,[OPEN],,2,-50,1,2,3,4,5,WIFI\n",
        ]
        self.assertEqual(_detect_flipper_marauder_log_style(lines), "classic")

    def test_header_starting_wardrive_forces_indexed(self):
        lines = [
            "\n",
            "Starting Wardrive. Stop with stopscan\n",
            "34:6b:46:ec:ba:0b,net,[WPA2],2026-01-01 00:00:00,1,-40,1,2,3,4,WIFI\n",
        ]
        self.assertEqual(_detect_flipper_marauder_log_style(lines), "indexed")

    def test_phase_b_first_classic_row(self):
        lines = [
            "# c\n",
            "34:6b:46:ec:ba:0b,net,[WPA2],2026-01-01 00:00:00,1,-40,1,2,3,4,WIFI\n",
        ]
        self.assertEqual(_detect_flipper_marauder_log_style(lines), "classic")

    def test_phase_b_indexed_prefix(self):
        lines = [
            "1 | aa:bb:cc:dd:ee:ff,,[OPEN],,2,-49,66.66,66.66,66.66,66.66,WIFI\n",
        ]
        self.assertEqual(_detect_flipper_marauder_log_style(lines), "indexed")


class ParseWifiIndexedTests(SimpleTestCase):
    def test_optional_timestamp_empty_field(self):
        line = (
            "1 | 9c:a7:d8:07:fb:94,,[OPEN],,2,-49,66.6600066,66.6600066,"
            "66.6600066,66.6600066,WIFI"
        )
        g = _parse_marauder_wifi_line(line)
        self.assertIsNotNone(g)
        mac, ssid, auth, ts, ch, rssi, lat, lon, alt, acc, dtype = g
        self.assertEqual(mac.lower(), "9c:a7:d8:07:fb:94")
        self.assertEqual(ts, "")
        self.assertEqual(ch, "2")
        self.assertEqual(dtype, "WIFI")


class ParseClassicAndMalformedTests(SimpleTestCase):
    def test_classic_wifi(self):
        line = (
            "34:6b:46:ec:ba:0b,TOTALPLAY,[WPA2_PSK],2026-03-25 00:22:27,11,-44,"
            "66.66,-66.66,66.66,66.66,WIFI"
        )
        g = _parse_marauder_line_classic(line)
        self.assertIsNotNone(g)
        self.assertEqual(g[-1], "WIFI")

    def test_malformed_device_ble(self):
        line = (
            "Device: d3vnull080:e1:26:76:33:64,,[BLE],2026-03-25 00:22:27,0,-27,"
            "66.66,-66.66,66.66,66.66,BLE"
        )
        g = _parse_marauder_ble_device_malformed(line)
        self.assertIsNotNone(g)
        self.assertEqual(g[0], "80:e1:26:76:33:64")
        self.assertEqual(g[-1], "BLE")

    def test_classic_parser_covers_malformed(self):
        line = (
            "Device: d3vnull080:e1:26:76:33:64,,[BLE],2026-03-25 00:22:27,0,-27,"
            "66.66,-66.66,66.66,66.66,BLE"
        )
        g = _parse_marauder_line_classic(line)
        self.assertIsNotNone(g)
        self.assertEqual(g[0], "80:e1:26:76:33:64")


class ProcessFormatV2MockTests(SimpleTestCase):
    @patch("apps.process.marauder.bulk_upsert_by_keys", return_value=(0, 0, 0))
    def test_v2_runs_without_db_rows(self, _mock_bulk):
        lines = [
            "StartingWardrive. Stop with stopscan\n",
            "34:6b:46:ec:ba:0b,x,[OPEN],2026-01-01 00:00:00,1,-40,1.0,2.0,3.0,4.0,WIFI\n",
        ]
        process_format_flipper_marauder_v2(lines=lines, uploaded_by="t")
        _mock_bulk.assert_called_once()
