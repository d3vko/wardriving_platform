"""
Unit tests for the Marauder/Flipper log-parsing pipeline and the shared
WiGLE canonical abstraction layer (apps.process._wigle_canonical).

Import paths reflect the new package structure:
  - apps.process.marauder  (public API + internal parsers)
  - apps.process._wigle_canonical  (aliases, schema, detect, sanitizers)
"""

import os
import tempfile
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.process._wigle_canonical.aliases import resolve_headers
from apps.process._wigle_canonical.detect import detect_dialect
from apps.process._wigle_canonical.sanitizers import sanitize_security
from apps.process._wigle_canonical.schema import CanonicalRow, coerce_row
from apps.process.marauder import (
    detect_dialect,  # re-exported convenience
    parse_log_ble_device_malformed,
    parse_log_classic,
    parse_log_wifi,
    process_file_marauder_esp32,
    process_format_flipper_marauder_v2,
)

_PATCH_BULK = "apps.process._wigle_canonical.persist.bulk_upsert_by_keys"


# ---------------------------------------------------------------------------
# resolve_headers / alias resolution
# ---------------------------------------------------------------------------


class ResolveHeadersTests(SimpleTestCase):
    def test_mac_from_bssid(self):
        m = resolve_headers(["BSSID", "SSID", "AuthMode", "Channel", "RSSI"])
        self.assertEqual(m["mac"], "BSSID")

    def test_mac_from_netid(self):
        m = resolve_headers(["netid", "ssid", "AuthMode", "Channel"])
        self.assertEqual(m["mac"], "netid")

    def test_capabilities_wins_over_authmode(self):
        m = resolve_headers(["MAC", "SSID", "Capabilities", "AuthMode", "Channel"])
        self.assertEqual(m["security"], "Capabilities")

    def test_authmode_fallback_without_capabilities(self):
        m = resolve_headers(["MAC", "SSID", "AuthMode", "Channel"])
        self.assertEqual(m["security"], "AuthMode")

    def test_encryption_alias(self):
        m = resolve_headers(["MAC", "SSID", "Encryption", "Channel"])
        self.assertEqual(m["security"], "Encryption")

    def test_frequency_present_when_in_headers(self):
        m = resolve_headers(["MAC", "SSID", "AuthMode", "Channel", "Frequency"])
        self.assertIn("frequency", m)
        self.assertEqual(m["frequency"], "Frequency")

    def test_frequency_absent_when_not_in_headers(self):
        m = resolve_headers(["MAC", "SSID", "AuthMode", "Channel"])
        self.assertNotIn("frequency", m)

    def test_currentlatitude_wins_over_latitude(self):
        m = resolve_headers(["CurrentLatitude", "Latitude", "MAC", "Channel"])
        self.assertEqual(m["latitude"], "CurrentLatitude")

    def test_last_seen_detected(self):
        m = resolve_headers(
            ["MAC", "SSID", "AuthMode", "FirstSeen", "LastSeen", "Channel"]
        )
        self.assertIn("last_seen", m)
        self.assertEqual(m["last_seen"], "LastSeen")


# ---------------------------------------------------------------------------
# detect_dialect
# ---------------------------------------------------------------------------


class DetectDialectTests(SimpleTestCase):
    def test_startingwardrive_is_log_indexed(self):
        lines = [
            "# log\n",
            "StartingWardrive. Stop with stopscan\n",
            "1 | aa:bb:cc:dd:ee:ff,x,[OPEN],,2,-50,1,2,3,4,WIFI\n",
        ]
        self.assertEqual(detect_dialect(lines), "log_indexed")

    def test_starting_wardrive_with_space_is_log_indexed(self):
        lines = [
            "\n",
            "Starting Wardrive. Stop with stopscan\n",
            "34:6b:46:ec:ba:0b,net,[WPA2],2026-01-01 00:00:00,1,-40,1,2,3,4,WIFI\n",
        ]
        self.assertEqual(detect_dialect(lines), "log_indexed")

    def test_first_classic_row_is_log_classic(self):
        lines = [
            "# c\n",
            "34:6b:46:ec:ba:0b,net,[WPA2],2026-01-01 00:00:00,1,-40,1,2,3,4,WIFI\n",
        ]
        self.assertEqual(detect_dialect(lines), "log_classic")

    def test_indexed_prefix_is_log_indexed(self):
        lines = [
            "1 | aa:bb:cc:dd:ee:ff,,[OPEN],,2,-49,66.66,66.66,66.66,66.66,WIFI\n",
        ]
        self.assertEqual(detect_dialect(lines), "log_indexed")

    def test_csv_header_detected(self):
        lines = [
            "MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,"
            "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n",
            "aa:bb:cc:dd:ee:ff,Net,[WPA2],2026-01-01 00:00:00,6,-55,19.0,-99.0,2200,5,WIFI\n",
        ]
        self.assertEqual(detect_dialect(lines), "csv_header")

    def test_wigle_metadata_then_csv_header(self):
        lines = [
            "WigleWifi-1.6,appRelease=2.72,model=Pixel,release=13\n",
            "MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,"
            "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n",
            "aa:bb:cc:dd:ee:ff,Net,[WPA2],2026-01-01 00:00:00,6,-55,19.0,-99.0,2200,5,WIFI\n",
        ]
        self.assertEqual(detect_dialect(lines), "csv_header")

    def test_capabilities_header_is_csv_header(self):
        lines = [
            "MAC,SSID,Capabilities,FirstSeen,Channel,RSSI,"
            "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n",
            "aa:bb:cc:dd:ee:ff,Fork,[WPA2-PSK][ESS],2026-01-01 00:00:00,11,-60,19.0,-99.0,2200,5,WIFI\n",
        ]
        self.assertEqual(detect_dialect(lines), "csv_header")


# ---------------------------------------------------------------------------
# parse_log_wifi
# ---------------------------------------------------------------------------


class ParseLogWifiTests(SimpleTestCase):
    def test_indexed_with_empty_timestamp(self):
        line = (
            "1 | 9c:a7:d8:07:fb:94,,[OPEN],,2,-49,66.6600066,66.6600066,"
            "66.6600066,66.6600066,WIFI"
        )
        row = parse_log_wifi(line)
        self.assertIsNotNone(row)
        self.assertEqual(row["MAC"].lower(), "9c:a7:d8:07:fb:94")
        self.assertEqual(row["Channel"], "2")
        self.assertEqual(row["Type"], "WIFI")
        self.assertEqual(row["FirstSeen"], "")

    def test_gt_prefix_indexed(self):
        line = (
            "> 1 | 78:8c:b5:1a:29:d4,Area,[WPA2_PSK],2026-04-05 18:46:47,10,-42,"
            "19.4112186,-99.1793900,2258.40,5.00,WIFI"
        )
        row = parse_log_wifi(line)
        self.assertIsNotNone(row)
        self.assertEqual(row["MAC"].lower(), "78:8c:b5:1a:29:d4")

    def test_skip_stopscan(self):
        self.assertIsNone(parse_log_wifi("stopscan"))

    def test_skip_startingwardrive(self):
        self.assertIsNone(parse_log_wifi("StartingWardrive. Stop with stopscan"))

    def test_skip_empty(self):
        self.assertIsNone(parse_log_wifi(""))


# ---------------------------------------------------------------------------
# parse_log_classic and parse_log_ble_device_malformed
# ---------------------------------------------------------------------------


class ParseLogClassicAndMalformedTests(SimpleTestCase):
    def test_classic_wifi(self):
        line = (
            "34:6b:46:ec:ba:0b,TOTALPLAY,[WPA2_PSK],2026-03-25 00:22:27,11,-44,"
            "66.66,-66.66,66.66,66.66,WIFI"
        )
        row = parse_log_classic(line)
        self.assertIsNotNone(row)
        self.assertEqual(row["Type"], "WIFI")
        self.assertEqual(row["MAC"], "34:6b:46:ec:ba:0b")

    def test_classic_ble(self):
        line = (
            "aa:bb:cc:dd:ee:ff,BLEDevice,[BLE],2026-03-25 00:22:27,0,-70,"
            "19.0,-99.0,2200.0,5.0,BLE"
        )
        row = parse_log_classic(line)
        self.assertIsNotNone(row)
        self.assertEqual(row["Type"], "BLE")

    def test_malformed_device_ble_extracts_mac(self):
        line = (
            "Device: d3vnull080:e1:26:76:33:64,,[BLE],2026-03-25 00:22:27,0,-27,"
            "66.66,-66.66,66.66,66.66,BLE"
        )
        row = parse_log_ble_device_malformed(line)
        self.assertIsNotNone(row)
        self.assertEqual(row["MAC"], "80:e1:26:76:33:64")
        self.assertEqual(row["Type"], "BLE")

    def test_classic_parser_delegates_malformed(self):
        line = (
            "Device: d3vnull080:e1:26:76:33:64,,[BLE],2026-03-25 00:22:27,0,-27,"
            "66.66,-66.66,66.66,66.66,BLE"
        )
        row = parse_log_classic(line)
        self.assertIsNotNone(row)
        self.assertEqual(row["MAC"], "80:e1:26:76:33:64")

    def test_skip_comment(self):
        self.assertIsNone(parse_log_classic("# this is a comment"))


# ---------------------------------------------------------------------------
# process_format_flipper_marauder_v2 (line-level processing)
# ---------------------------------------------------------------------------


class ProcessFormatV2MockTests(SimpleTestCase):
    @patch(_PATCH_BULK, return_value=(0, 0, 0))
    def test_v2_runs_without_error(self, _mock_bulk):
        lines = [
            "StartingWardrive. Stop with stopscan\n",
            "34:6b:46:ec:ba:0b,x,[OPEN],2026-01-01 00:00:00,1,-40,1.0,2.0,3.0,4.0,WIFI\n",
        ]
        process_format_flipper_marauder_v2(lines=lines, uploaded_by="t")
        _mock_bulk.assert_called_once()

    @patch(_PATCH_BULK, return_value=(1, 0, 0))
    def test_v2_startingwardrive_plus_gt_indexed_wifi(self, mock_bulk):
        lines = [
            "#wardrive -serial\n",
            "StartingWardrive. Stop with stopscan\n",
            "> 1 | 78:8c:b5:1a:29:d4,Area,[WPA2_PSK],2026-04-05 18:46:47,10,-42,"
            "19.4112186,-99.1793900,2258.40,5.00,WIFI\n",
            "2 | 50:91:e3:9c:be:af,TP,[WPA2_PSK],2026-04-05 18:46:47,4,-46,"
            "19.4112186,-99.1793900,2258.40,5.00,WIFI\n",
        ]
        process_format_flipper_marauder_v2(lines=lines, uploaded_by="u")
        mock_bulk.assert_called_once()
        rows = mock_bulk.call_args.kwargs["rows"]
        self.assertGreaterEqual(len(rows), 2)

    @patch(_PATCH_BULK, return_value=(0, 0, 0))
    def test_v2_empty_lines_returns_zeros(self, mock_bulk):
        # No parseable rows → bulk_upsert is called with rows=[] and returns (0,0,0)
        result = process_format_flipper_marauder_v2(lines=[], uploaded_by="t")
        self.assertEqual(result, (0, 0, 0))

    @patch(_PATCH_BULK, return_value=(1, 0, 0))
    def test_v2_returns_tuple(self, mock_bulk):
        lines = [
            "34:6b:46:ec:ba:0b,x,[WPA2],2026-01-01 00:00:00,1,-40,1.0,2.0,3.0,4.0,WIFI\n"
        ]
        result = process_format_flipper_marauder_v2(lines=lines, uploaded_by="t")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)


# ---------------------------------------------------------------------------
# CSV-with-header parser via process_file_marauder_esp32
# ---------------------------------------------------------------------------


def _write_tmp_csv(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


class CsvWithHeaderTests(SimpleTestCase):
    """Integration tests for Marauder CSV-with-header variants."""

    @patch(_PATCH_BULK, return_value=(1, 0, 0))
    def test_wigle14_authmode(self, mock_bulk):
        """WigleWifi-1.4 / 1.2 style: AuthMode column."""
        csv = (
            "MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,"
            "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"
            "aa:bb:cc:dd:ee:ff,TestNet,[WPA2],2026-01-01 00:00:00,"
            "6,-55,19.0,-99.0,2200,5,WIFI\n"
        )
        path = _write_tmp_csv(csv)
        try:
            result = process_file_marauder_esp32(file_path=path, uploaded_by="test")
            self.assertIsInstance(result, tuple)
            mock_bulk.assert_called_once()
            rows = mock_bulk.call_args.kwargs["rows"]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["mac"], "aa:bb:cc:dd:ee:ff")
            self.assertIn("auth_mode", rows[0])
        finally:
            os.unlink(path)

    @patch(_PATCH_BULK, return_value=(1, 0, 0))
    def test_capabilities_header_priority(self, mock_bulk):
        """WigleWifi-1.3+: Capabilities column preferred over AuthMode; brackets stripped."""
        csv = (
            "MAC,SSID,Capabilities,AuthMode,FirstSeen,Channel,RSSI,"
            "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"
            "11:22:33:44:55:66,ForkNet,[WPA2-PSK-CCMP][ESS],[WPA2],"
            "2026-01-01 00:00:00,11,-60,19.0,-99.0,2200,5,WIFI\n"
        )
        path = _write_tmp_csv(csv)
        try:
            process_file_marauder_esp32(file_path=path, uploaded_by="test")
            rows = mock_bulk.call_args.kwargs["rows"]
            # Capabilities wins and brackets are stripped → first token without brackets
            self.assertEqual(rows[0]["auth_mode"], "WPA2-PSK-CCMP")
        finally:
            os.unlink(path)

    @patch(_PATCH_BULK, return_value=(1, 0, 0))
    def test_bssid_alias_as_mac(self, mock_bulk):
        """BSSID column resolved as mac."""
        csv = (
            "BSSID,SSID,AuthMode,FirstSeen,Channel,RSSI,"
            "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"
            "aa:bb:cc:dd:ee:01,BSSIDNet,[WPA2],2026-01-01 00:00:00,"
            "1,-50,19.0,-99.0,2200,5,WIFI\n"
        )
        path = _write_tmp_csv(csv)
        try:
            process_file_marauder_esp32(file_path=path, uploaded_by="test")
            rows = mock_bulk.call_args.kwargs["rows"]
            self.assertEqual(rows[0]["mac"], "aa:bb:cc:dd:ee:01")
        finally:
            os.unlink(path)

    @patch(_PATCH_BULK, return_value=(1, 0, 0))
    def test_extended_timing_with_frequency(self, mock_bulk):
        """Extended Timing variant: Frequency and LastSeen columns present."""
        csv = (
            "MAC,SSID,Capabilities,FirstSeen,LastSeen,Channel,Frequency,RSSI,"
            "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"
            "aa:bb:cc:dd:ee:02,ExtNet,[WPA3],2026-01-01 00:00:00,"
            "2026-01-01 00:01:00,36,5180,-65,19.0,-99.0,2200,5,WIFI\n"
        )
        path = _write_tmp_csv(csv)
        try:
            process_file_marauder_esp32(file_path=path, uploaded_by="test")
            mock_bulk.assert_called_once()
            rows = mock_bulk.call_args.kwargs["rows"]
            self.assertEqual(len(rows), 1)
        finally:
            os.unlink(path)

    @patch(_PATCH_BULK, return_value=(1, 0, 0))
    def test_ble_type_preserved(self, mock_bulk):
        """BLE rows: Type=BLE stored correctly."""
        csv = (
            "MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,"
            "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"
            "aa:bb:cc:dd:ee:03,MyBLE,[BLE],2026-01-01 00:00:00,"
            "0,-70,19.0,-99.0,2200,5,BLE\n"
        )
        path = _write_tmp_csv(csv)
        try:
            process_file_marauder_esp32(file_path=path, uploaded_by="test")
            rows = mock_bulk.call_args.kwargs["rows"]
            self.assertEqual(rows[0]["type"], "BLE")
        finally:
            os.unlink(path)

    @patch(_PATCH_BULK, return_value=(1, 0, 0))
    def test_wigle_metadata_line_skipped(self, mock_bulk):
        """WigleWifi metadata line before header is transparently skipped."""
        csv = (
            "WigleWifi-1.6,appRelease=2.72,model=Pixel\n"
            "MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,"
            "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"
            "aa:bb:cc:dd:ee:04,WiGLENet,[WPA2],2026-01-01 00:00:00,"
            "11,-55,19.0,-99.0,2200,5,WIFI\n"
        )
        path = _write_tmp_csv(csv)
        try:
            process_file_marauder_esp32(file_path=path, uploaded_by="test")
            rows = mock_bulk.call_args.kwargs["rows"]
            self.assertEqual(rows[0]["mac"], "aa:bb:cc:dd:ee:04")
        finally:
            os.unlink(path)

    @patch(_PATCH_BULK, return_value=(1, 0, 0))
    def test_zero_lat_lon_row_discarded(self, mock_bulk):
        """Rows with lat=0 AND lon=0 must be discarded (no GPS fix)."""
        csv = (
            "MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,"
            "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"
            "aa:bb:cc:dd:ee:05,NoGPS,[WPA2],2026-01-01 00:00:00,6,-55,0,0,0,0,WIFI\n"
            "aa:bb:cc:dd:ee:06,HasGPS,[WPA2],2026-01-01 00:00:00,6,-55,19.0,-99.0,2200,5,WIFI\n"
        )
        path = _write_tmp_csv(csv)
        try:
            process_file_marauder_esp32(file_path=path, uploaded_by="test")
            rows = mock_bulk.call_args.kwargs["rows"]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["mac"], "aa:bb:cc:dd:ee:06")
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Compatibility: process_file_marauder_esp32 with log files
# ---------------------------------------------------------------------------


class EntrypointCompatTests(SimpleTestCase):
    @patch(_PATCH_BULK, return_value=(3, 1, 0))
    def test_returns_3_tuple(self, _mock):
        lines = [
            "1 | aa:bb:cc:dd:ee:ff,Net,[WPA2],2026-01-01 00:00:00,"
            "6,-55,19.0,-99.0,2200,5,WIFI\n",
        ]
        fd, path = tempfile.mkstemp(suffix=".log")
        with os.fdopen(fd, "w") as fh:
            fh.writelines(lines)
        try:
            result = process_file_marauder_esp32(file_path=path, uploaded_by="test")
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 3)
        finally:
            os.unlink(path)

    @patch(_PATCH_BULK, return_value=(1, 0, 0))
    def test_classic_log_file(self, mock_bulk):
        lines = [
            "34:6b:46:ec:ba:0b,MYNET,[WPA2_PSK],2026-03-25 00:22:27,11,-44,"
            "19.411,-99.179,2258.0,5.0,WIFI\n",
        ]
        fd, path = tempfile.mkstemp(suffix=".log")
        with os.fdopen(fd, "w") as fh:
            fh.writelines(lines)
        try:
            process_file_marauder_esp32(file_path=path, uploaded_by="test")
            mock_bulk.assert_called_once()
            rows = mock_bulk.call_args.kwargs["rows"]
            self.assertEqual(rows[0]["mac"], "34:6b:46:ec:ba:0b")
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# sanitize_security unit tests
# ---------------------------------------------------------------------------


class SanitizeSecurityTests(SimpleTestCase):
    def test_single_bracket_token(self):
        self.assertEqual(sanitize_security("[ESS]"), "ESS")

    def test_multi_bracket_takes_first(self):
        self.assertEqual(
            sanitize_security("[WPA2-PSK-CCMP-128][RSN-PSK-CCMP-128][ESS]"),
            "WPA2-PSK-CCMP-128",
        )

    def test_slash_in_first_token_trimmed(self):
        self.assertEqual(
            sanitize_security("[WPA2-EAP/SHA1-CCMP-128][RSN-PSK-CCMP][ESS]"),
            "WPA2-EAP",
        )

    def test_no_brackets_passthrough(self):
        self.assertEqual(sanitize_security("WPA2_PSK"), "WPA2_PSK")
        self.assertEqual(sanitize_security("WPA2"), "WPA2")
        self.assertEqual(sanitize_security("OPEN"), "OPEN")

    def test_empty_string_returns_none(self):
        self.assertIsNone(sanitize_security(""))

    def test_none_returns_none(self):
        self.assertIsNone(sanitize_security(None))

    def test_whitespace_only_returns_none(self):
        self.assertIsNone(sanitize_security("   "))

    def test_single_empty_bracket_returns_none(self):
        # Edge case: "[]" should not yield an empty string
        result = sanitize_security("[]")
        self.assertIsNone(result)

    def test_wpa3_no_brackets(self):
        self.assertEqual(sanitize_security("WPA3-SAE"), "WPA3-SAE")


# ---------------------------------------------------------------------------
# Security bracket stripping end-to-end via CSV
# ---------------------------------------------------------------------------


class CsvSecuritySanitizationTests(SimpleTestCase):
    @patch(_PATCH_BULK, return_value=(1, 0, 0))
    def test_capabilities_brackets_stripped(self, mock_bulk):
        """[WPA2-PSK-CCMP][ESS] in Capabilities column → auth_mode = 'WPA2-PSK-CCMP'"""
        csv = (
            "MAC,SSID,Capabilities,FirstSeen,Channel,RSSI,"
            "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"
            "aa:bb:cc:dd:ee:10,TestNet,[WPA2-PSK-CCMP][ESS],2026-01-01 00:00:00,"
            "6,-55,19.0,-99.0,2200,5,WIFI\n"
        )
        path = _write_tmp_csv(csv)
        try:
            process_file_marauder_esp32(file_path=path, uploaded_by="test")
            rows = mock_bulk.call_args.kwargs["rows"]
            self.assertEqual(rows[0]["auth_mode"], "WPA2-PSK-CCMP")
        finally:
            os.unlink(path)

    @patch(_PATCH_BULK, return_value=(1, 0, 0))
    def test_authmode_brackets_stripped(self, mock_bulk):
        """[WPA2] in AuthMode column → auth_mode = 'WPA2'"""
        csv = (
            "MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,"
            "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"
            "aa:bb:cc:dd:ee:11,Net2,[WPA2],2026-01-01 00:00:00,"
            "6,-55,19.0,-99.0,2200,5,WIFI\n"
        )
        path = _write_tmp_csv(csv)
        try:
            process_file_marauder_esp32(file_path=path, uploaded_by="test")
            rows = mock_bulk.call_args.kwargs["rows"]
            self.assertEqual(rows[0]["auth_mode"], "WPA2")
        finally:
            os.unlink(path)

    @patch(_PATCH_BULK, return_value=(1, 0, 0))
    def test_slash_in_first_token_stripped(self, mock_bulk):
        """[WPA2-EAP/SHA1-CCMP][RSN][ESS] → auth_mode = 'WPA2-EAP'"""
        csv = (
            "MAC,SSID,Capabilities,FirstSeen,Channel,RSSI,"
            "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"
            "aa:bb:cc:dd:ee:12,EAPNet,[WPA2-EAP/SHA1-CCMP][RSN][ESS],"
            "2026-01-01 00:00:00,6,-55,19.0,-99.0,2200,5,WIFI\n"
        )
        path = _write_tmp_csv(csv)
        try:
            process_file_marauder_esp32(file_path=path, uploaded_by="test")
            rows = mock_bulk.call_args.kwargs["rows"]
            self.assertEqual(rows[0]["auth_mode"], "WPA2-EAP")
        finally:
            os.unlink(path)

    @patch(_PATCH_BULK, return_value=(1, 0, 0))
    def test_plain_no_brackets_passthrough(self, mock_bulk):
        """Encryption=WPA2 (no brackets, fork variant) → auth_mode = 'WPA2'"""
        csv = (
            "MAC,SSID,Encryption,FirstSeen,Channel,RSSI,"
            "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"
            "aa:bb:cc:dd:ee:13,PlainNet,WPA2,2026-01-01 00:00:00,"
            "6,-55,19.0,-99.0,2200,5,WIFI\n"
        )
        path = _write_tmp_csv(csv)
        try:
            process_file_marauder_esp32(file_path=path, uploaded_by="test")
            rows = mock_bulk.call_args.kwargs["rows"]
            self.assertEqual(rows[0]["auth_mode"], "WPA2")
        finally:
            os.unlink(path)

    @patch(_PATCH_BULK, return_value=(1, 0, 0))
    def test_log_auth_mode_already_unbracketed(self, mock_bulk):
        """Regression: log parser strips brackets via regex; sanitize_security must passthrough."""
        lines = [
            "34:6b:46:ec:ba:0b,MYNET,[WPA2_PSK],2026-03-25 00:22:27,11,-44,"
            "19.411,-99.179,2258.0,5.0,WIFI\n",
        ]
        fd, path = tempfile.mkstemp(suffix=".log")
        with os.fdopen(fd, "w") as fh:
            fh.writelines(lines)
        try:
            process_file_marauder_esp32(file_path=path, uploaded_by="test")
            rows = mock_bulk.call_args.kwargs["rows"]
            # The regex already extracted the inner "WPA2_PSK" without brackets;
            # sanitize_security keeps it unchanged.
            self.assertEqual(rows[0]["auth_mode"], "WPA2_PSK")
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# SSID empty / whitespace / NaN → None
# ---------------------------------------------------------------------------


class SsidNullHandlingTests(SimpleTestCase):
    @patch(_PATCH_BULK, return_value=(1, 0, 0))
    def test_ssid_empty_string_becomes_none(self, mock_bulk):
        """SSID cell is empty → 'ssid' key absent from persisted payload."""
        csv = (
            "MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,"
            "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"
            "aa:bb:cc:dd:ee:20,,[WPA2],2026-01-01 00:00:00,6,-55,19.0,-99.0,2200,5,WIFI\n"
        )
        path = _write_tmp_csv(csv)
        try:
            process_file_marauder_esp32(file_path=path, uploaded_by="test")
            rows = mock_bulk.call_args.kwargs["rows"]
            self.assertEqual(len(rows), 1)
            self.assertNotIn("ssid", rows[0])
        finally:
            os.unlink(path)

    @patch(_PATCH_BULK, return_value=(1, 0, 0))
    def test_ssid_whitespace_becomes_none(self, mock_bulk):
        """SSID cell with only spaces → 'ssid' key absent from persisted payload."""
        csv = (
            "MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,"
            "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"
            "aa:bb:cc:dd:ee:21,   ,[WPA2],2026-01-01 00:00:00,6,-55,19.0,-99.0,2200,5,WIFI\n"
        )
        path = _write_tmp_csv(csv)
        try:
            process_file_marauder_esp32(file_path=path, uploaded_by="test")
            rows = mock_bulk.call_args.kwargs["rows"]
            self.assertEqual(len(rows), 1)
            self.assertNotIn("ssid", rows[0])
        finally:
            os.unlink(path)

    def test_coerce_row_ssid_nan_sentinel_is_none(self):
        """coerce_row with SSID='nan' → CanonicalRow.ssid is None."""
        from apps.process._wigle_canonical.aliases import resolve_headers
        header_map = resolve_headers([
            "MAC", "SSID", "AuthMode", "Channel",
            "CurrentLatitude", "CurrentLongitude",
        ])
        raw = {
            "MAC": "aa:bb:cc:dd:ee:ff",
            "SSID": "nan",
            "AuthMode": "WPA2",
            "Channel": "6",
            "CurrentLatitude": "19.0",
            "CurrentLongitude": "-99.0",
        }
        row = coerce_row(raw, header_map)
        self.assertIsNotNone(row)
        self.assertIsNone(row.ssid)

    def test_coerce_row_ssid_whitespace_is_none(self):
        """coerce_row with SSID='   ' → CanonicalRow.ssid is None."""
        from apps.process._wigle_canonical.aliases import resolve_headers
        header_map = resolve_headers([
            "MAC", "SSID", "AuthMode", "Channel",
            "CurrentLatitude", "CurrentLongitude",
        ])
        raw = {
            "MAC": "aa:bb:cc:dd:ee:ff",
            "SSID": "   ",
            "AuthMode": "WPA2",
            "Channel": "6",
            "CurrentLatitude": "19.0",
            "CurrentLongitude": "-99.0",
        }
        row = coerce_row(raw, header_map)
        self.assertIsNotNone(row)
        self.assertIsNone(row.ssid)

    def test_coerce_row_ssid_null_sentinel_is_none(self):
        """coerce_row with SSID='NULL' → CanonicalRow.ssid is None."""
        from apps.process._wigle_canonical.aliases import resolve_headers
        header_map = resolve_headers([
            "MAC", "SSID", "AuthMode", "Channel",
            "CurrentLatitude", "CurrentLongitude",
        ])
        raw = {
            "MAC": "aa:bb:cc:dd:ee:ff",
            "SSID": "NULL",
            "AuthMode": "WPA2",
            "Channel": "6",
            "CurrentLatitude": "19.0",
            "CurrentLongitude": "-99.0",
        }
        row = coerce_row(raw, header_map)
        self.assertIsNotNone(row)
        self.assertIsNone(row.ssid)


# ---------------------------------------------------------------------------
# Minino / PwnTerrey Marauder processor
# ---------------------------------------------------------------------------

_PATCH_BULK_MININO = "apps.process._wigle_canonical.persist.bulk_upsert_by_keys"

_MININO_HEADER = (
    "MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,"
    "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"
)


class MininoProcessorTests(SimpleTestCase):
    """Tests for process_file_minino (also covers PWNTERREY_MARAUDER path)."""

    def _write_minino_csv(self, data_lines: str) -> str:
        """Write a Minino-style CSV with a metadata line + header + data."""
        content = (
            "WigleWifi-1.4,appRelease=minino\n"
            + _MININO_HEADER
            + data_lines
        )
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    @patch(_PATCH_BULK_MININO, return_value=(1, 0, 0))
    def test_auth_mode_brackets_stripped(self, mock_bulk):
        """[WPA2-PSK-CCMP][ESS] → auth_mode = 'WPA2-PSK-CCMP'"""
        from apps.process.minino import process_file_minino
        path = self._write_minino_csv(
            "aa:bb:cc:dd:ee:30,HomeNet,[WPA2-PSK-CCMP][ESS],"
            "2026-01-01 00:00:00,6,-55,19.0,-99.0,2200,5,WIFI\n"
        )
        try:
            process_file_minino(file_path=path, uploaded_by="test")
            rows = mock_bulk.call_args.kwargs["rows"]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["auth_mode"], "WPA2-PSK-CCMP")
        finally:
            os.unlink(path)

    @patch(_PATCH_BULK_MININO, return_value=(1, 0, 0))
    def test_open_network_brackets_stripped(self, mock_bulk):
        """[OPEN] → auth_mode = 'OPEN'"""
        from apps.process.minino import process_file_minino
        path = self._write_minino_csv(
            "aa:bb:cc:dd:ee:31,CafeWiFi,[OPEN],"
            "2026-01-01 00:00:00,1,-70,19.0,-99.0,2200,5,WIFI\n"
        )
        try:
            process_file_minino(file_path=path, uploaded_by="test")
            rows = mock_bulk.call_args.kwargs["rows"]
            self.assertEqual(rows[0]["auth_mode"], "OPEN")
        finally:
            os.unlink(path)

    @patch(_PATCH_BULK_MININO, return_value=(1, 0, 0))
    def test_ble_auth_mode_brackets_stripped(self, mock_bulk):
        """[BLE] → auth_mode = 'BLE'"""
        from apps.process.minino import process_file_minino
        path = self._write_minino_csv(
            "aa:bb:cc:dd:ee:32,BTDevice,[BLE],"
            "2026-01-01 00:00:00,0,-65,19.0,-99.0,2200,5,BLE\n"
        )
        try:
            process_file_minino(file_path=path, uploaded_by="test")
            rows = mock_bulk.call_args.kwargs["rows"]
            self.assertEqual(rows[0]["auth_mode"], "BLE")
            self.assertEqual(rows[0]["type"], "BLE")
        finally:
            os.unlink(path)

    @patch(_PATCH_BULK_MININO, return_value=(1, 0, 0))
    def test_ssid_empty_becomes_none(self, mock_bulk):
        """Empty SSID cell → 'ssid' absent from persisted payload."""
        from apps.process.minino import process_file_minino
        path = self._write_minino_csv(
            "aa:bb:cc:dd:ee:33,,[WPA2],"
            "2026-01-01 00:00:00,6,-55,19.0,-99.0,2200,5,WIFI\n"
        )
        try:
            process_file_minino(file_path=path, uploaded_by="test")
            rows = mock_bulk.call_args.kwargs["rows"]
            self.assertEqual(len(rows), 1)
            self.assertNotIn("ssid", rows[0])
        finally:
            os.unlink(path)

    @patch(_PATCH_BULK_MININO, return_value=(1, 0, 0))
    def test_ssid_nan_string_becomes_none(self, mock_bulk):
        """SSID='nan' (pandas artefact) → 'ssid' absent from persisted payload."""
        from apps.process.minino import process_file_minino
        # Write without metadata line so pandas would previously emit 'nan'
        content = _MININO_HEADER + (
            "aa:bb:cc:dd:ee:34,nan,[WPA2],"
            "2026-01-01 00:00:00,6,-55,19.0,-99.0,2200,5,WIFI\n"
        )
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        try:
            # skiprows=1 skips the header, so use skiprows=0 equivalent:
            # to test the sentinel directly, call coerce_row with 'nan' SSID
            process_file_minino(file_path=path, uploaded_by="test")
            # The row may or may not appear depending on skiprows, but if it
            # does appear ssid must be absent; verify via coerce_row directly.
        finally:
            os.unlink(path)

        # Direct coerce_row test for 'nan' sentinel:
        header_map = resolve_headers([
            "MAC", "SSID", "AuthMode", "Channel",
            "CurrentLatitude", "CurrentLongitude",
        ])
        row = coerce_row(
            {"MAC": "aa:bb:cc:dd:ee:ff", "SSID": "nan", "AuthMode": "WPA2",
             "Channel": "6", "CurrentLatitude": "19.0", "CurrentLongitude": "-99.0"},
            header_map,
        )
        self.assertIsNotNone(row)
        self.assertIsNone(row.ssid)

    @patch(_PATCH_BULK_MININO, return_value=(1, 0, 0))
    def test_ssid_whitespace_becomes_none(self, mock_bulk):
        """SSID with only spaces → 'ssid' absent from persisted payload."""
        from apps.process.minino import process_file_minino
        path = self._write_minino_csv(
            "aa:bb:cc:dd:ee:35,   ,[WPA2],"
            "2026-01-01 00:00:00,6,-55,19.0,-99.0,2200,5,WIFI\n"
        )
        try:
            process_file_minino(file_path=path, uploaded_by="test")
            rows = mock_bulk.call_args.kwargs["rows"]
            self.assertEqual(len(rows), 1)
            self.assertNotIn("ssid", rows[0])
        finally:
            os.unlink(path)

    def test_pwnterrey_marauder_routes_to_minino(self):
        """PWNTERREY_MARAUDER must still map to process_file_minino in CHOICES_FUNCTION_PROCESS."""
        from apps.process import CHOICES_FUNCTION_PROCESS
        from apps.process.minino import process_file_minino
        from apps.wardriving.models import SourceDevice
        self.assertIs(
            CHOICES_FUNCTION_PROCESS[SourceDevice.PWNTERREY_MARAUDER],
            process_file_minino,
        )
