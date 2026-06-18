"""
Unit tests for process_lte_wardriving (apps.process.rf) and
process_file_lte_android (apps.process.android).

Covers:
  - Legacy ES/EN CSV (15 columns, no TipoCelda/eNodeB/PCI/EARFCN)
  - Extended firmware/serial CSV (23 columns, serving + neighbor rows)
  - Serial WebSerial export with leading "Source" column
  - Placeholder rows are filtered (CellID sentinel, LAC sentinel, MCC=0, no GPS)
  - Timestamp column drives first_seen (not now())
  - eNodeB / sector_id derived from cell_id when absent
  - process_file_lte_android wrapper reads CSV file and delegates correctly

Data policy: all CSV fixtures below use SYNTHETIC data — no real GPS captures,
no real cell IDs from field sessions.  See .cursor/skills/wardriving-test-data-policy/SKILL.md.
"""

import io
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

from django.test import SimpleTestCase
from pandas import read_csv

from apps.process.rf import process_lte_wardriving
from apps.wardriving import LteCellType

_PATCH_BULK = "apps.process.rf.bulk_upsert_by_keys"

# Synthetic test data — clearly fictitious, never copied from field captures.
_SYN_LAT = "10.5000001"
_SYN_LON = "-70.5000001"
_SYN_MCC = 310
_SYN_MNC = 410
_SYN_LAC = 10001
_SYN_OPERATOR = "TestCarrier"
_SYN_CELL_LEGACY = [25600001, 25600002, 25600003]  # eNodeB=100000, sectors 1-3
_SYN_CELL_EXTENDED = 25600021  # eNodeB=100000, sector=21
_SYN_CELL_MISSING_FREQ = 25600010  # eNodeB=100000, sector=10
_SYN_ENODEB = 100000
_SYN_SECTOR = 21
_SYN_PCI = 12
_SYN_EARFCN = 50001
_SYN_LAC_SERIAL = 20002
_SYN_CELL_SERIAL = 25600015  # eNodeB=100000, sector=15
_SYN_PCI_SERIAL = 4
_SYN_PCI_NEIGHBOR = 23
_SYN_PCI_SERIAL_NEIGHBOR = 44


def _df(csv_text: str):
    return read_csv(io.StringIO(csv_text), sep=",", low_memory=False)


# ---------------------------------------------------------------------------
# Legacy format (15-column English, as produced by Android / old firmware)
# ---------------------------------------------------------------------------

LEGACY_EN_CSV = f"""\
Timestamp,Technology,State,MCC,MNC,LAC,CellID,Band,RSSI,RSRP,RSRQ,SINR,Operator,Longitude,Latitude
2025-06-14 15:00:01,LTE,1,{_SYN_MCC},{_SYN_MNC},{_SYN_LAC},{_SYN_CELL_LEGACY[0]},7,-106,-106,-8,0,{_SYN_OPERATOR},{_SYN_LON},{_SYN_LAT}
1970-01-01 03:27:06,LTE,0,000,00,65535,268435455,,-106,-106,-7,0,{_SYN_OPERATOR},,
2025-06-14 15:00:02,LTE,1,{_SYN_MCC},{_SYN_MNC},{_SYN_LAC},{_SYN_CELL_LEGACY[1]},7,-100,-100,-7,2,{_SYN_OPERATOR},{_SYN_LON},{_SYN_LAT}
"""

# Legacy Spanish (RF firmware)
LEGACY_ES_CSV = f"""\
Timestamp,Tecnología,Estado,MCC,MNC,LAC,CellID,Banda,RSSI,RSRP,RSRQ,SINR,Operador,Longitud,Latitud
2025-06-14 15:00:03,LTE,1,{_SYN_MCC},{_SYN_MNC},{_SYN_LAC},{_SYN_CELL_LEGACY[2]},7,-103,-103,-9,0,{_SYN_OPERATOR},{_SYN_LON},{_SYN_LAT}
"""

# Extended firmware schema — valid row with empty FreqDL_MHz / FreqUL_MHz
EXTENDED_MISSING_FREQ_CSV = f"""\
Timestamp,Tecnología,TipoCelda,Estado,MCC,MNC,LAC,CellID,eNodeB,Sector,PCI,Banda,EARFCN,FreqDL_MHz,FreqUL_MHz,RSSI,RSRP,RSRQ,SINR,Operador,Longitud,Latitud
2025-06-14 15:00:05,LTE,serving,1,{_SYN_MCC},{_SYN_MNC},{_SYN_LAC},{_SYN_CELL_MISSING_FREQ},{_SYN_ENODEB},10,{_SYN_PCI},48,{_SYN_EARFCN},,,-85,-93,-12,8,{_SYN_OPERATOR},{_SYN_LON},{_SYN_LAT}
"""

# Extended firmware schema with serving + neighbor rows
EXTENDED_CSV = f"""\
Timestamp,Tecnología,TipoCelda,Estado,MCC,MNC,LAC,CellID,eNodeB,Sector,PCI,Banda,EARFCN,FreqDL_MHz,FreqUL_MHz,RSSI,RSRP,RSRQ,SINR,Operador,Longitud,Latitud
2025-06-14 15:00:05,LTE,serving,1,{_SYN_MCC},{_SYN_MNC},{_SYN_LAC},{_SYN_CELL_EXTENDED},{_SYN_ENODEB},{_SYN_SECTOR},{_SYN_SECTOR},7,2825,2627.5,2507.5,-85,-93,-12,8,{_SYN_OPERATOR},{_SYN_LON},{_SYN_LAT}
2025-06-14 15:00:05,LTE,neighbor,1,{_SYN_MCC},{_SYN_MNC},{_SYN_LAC},0,0,0,{_SYN_PCI_NEIGHBOR},7,2825,2627.5,2507.5,0,-91,-11,0,{_SYN_OPERATOR},{_SYN_LON},{_SYN_LAT}
"""

# Serial WebSerial export — identical to extended but prefixed with Source column
SERIAL_SOURCE_CSV = f"""\
Source,Timestamp,Tecnología,TipoCelda,Estado,MCC,MNC,LAC,CellID,eNodeB,Sector,PCI,Banda,EARFCN,FreqDL_MHz,FreqUL_MHz,RSSI,RSRP,RSRQ,SINR,Operador,Longitud,Latitud
lte,2025-06-14 15:00:10,LTE,serving,1,{_SYN_MCC},{_SYN_MNC},{_SYN_LAC_SERIAL},{_SYN_CELL_SERIAL},{_SYN_ENODEB},15,{_SYN_PCI_SERIAL},7,2825,2627.5,2507.5,-80,-88,-10,5,{_SYN_OPERATOR},{_SYN_LON},{_SYN_LAT}
lte,2025-06-14 15:00:10,LTE,neighbor,1,{_SYN_MCC},{_SYN_MNC},{_SYN_LAC_SERIAL},0,0,0,{_SYN_PCI_SERIAL_NEIGHBOR},7,2825,2627.5,2507.5,0,-95,-13,0,{_SYN_OPERATOR},{_SYN_LON},{_SYN_LAT}
"""


def _captured_rows(csv_text: str) -> list[dict]:
    """Run parser and return the rows list captured from bulk_upsert_by_keys."""
    captured = []

    def fake_bulk(*, model, key_fields, rows, **kwargs):
        captured.extend(rows)
        return len(rows), 0, 0

    with patch(_PATCH_BULK, side_effect=fake_bulk):
        process_lte_wardriving(dataframe=_df(csv_text))

    return captured


class LegacyEnglishFormatTests(SimpleTestCase):
    def test_valid_rows_persisted(self):
        rows = _captured_rows(LEGACY_EN_CSV)
        # Row 1 is valid, row 2 is a placeholder (LAC 65535 / CellID sentinel),
        # row 3 is valid.
        self.assertEqual(len(rows), 2)

    def test_first_seen_from_timestamp(self):
        rows = _captured_rows(LEGACY_EN_CSV)
        ts = rows[0]["first_seen"]
        # Must NOT be "now" — timestamp in CSV is 2025-06-14
        self.assertEqual(ts.year, 2025)
        self.assertEqual(ts.month, 6)
        self.assertEqual(ts.day, 14)

    def test_default_cell_type_is_serving(self):
        rows = _captured_rows(LEGACY_EN_CSV)
        for row in rows:
            self.assertEqual(row["cell_type"], LteCellType.SERVING)

    def test_enodeb_derived_from_cell_id(self):
        rows = _captured_rows(LEGACY_EN_CSV)
        row = rows[0]
        self.assertEqual(row["enodeb_id"], row["cell_id"] // 256)
        self.assertEqual(row["sector_id"], row["cell_id"] % 256)

    def test_placeholder_rows_filtered(self):
        rows = _captured_rows(LEGACY_EN_CSV)
        cell_ids = [r["cell_id"] for r in rows]
        self.assertNotIn(268435455, cell_ids)


class LegacySpanishFormatTests(SimpleTestCase):
    def test_valid_row_persisted(self):
        rows = _captured_rows(LEGACY_ES_CSV)
        self.assertEqual(len(rows), 1)

    def test_provider_field_mapped(self):
        rows = _captured_rows(LEGACY_ES_CSV)
        self.assertEqual(rows[0]["provider"], _SYN_OPERATOR)


class ExtendedFormatTests(SimpleTestCase):
    def test_serving_and_neighbor_both_persisted(self):
        rows = _captured_rows(EXTENDED_CSV)
        self.assertEqual(len(rows), 2)
        cell_types = {r["cell_type"] for r in rows}
        self.assertIn(LteCellType.SERVING, cell_types)
        self.assertIn(LteCellType.NEIGHBOR, cell_types)

    def test_neighbor_cell_id_zero_is_kept(self):
        rows = _captured_rows(EXTENDED_CSV)
        neighbor = next(r for r in rows if r["cell_type"] == LteCellType.NEIGHBOR)
        self.assertEqual(neighbor["cell_id"], 0)

    def test_pci_earfcn_populated(self):
        rows = _captured_rows(EXTENDED_CSV)
        serving = next(r for r in rows if r["cell_type"] == LteCellType.SERVING)
        self.assertEqual(serving["pci"], _SYN_SECTOR)
        self.assertEqual(serving["earfcn"], 2825)

    def test_freq_fields_populated(self):
        rows = _captured_rows(EXTENDED_CSV)
        serving = next(r for r in rows if r["cell_type"] == LteCellType.SERVING)
        self.assertAlmostEqual(float(serving["dl_freq_mhz"]), 2627.5)
        self.assertAlmostEqual(float(serving["ul_freq_mhz"]), 2507.5)

    def test_enodeb_sector_from_csv(self):
        rows = _captured_rows(EXTENDED_CSV)
        serving = next(r for r in rows if r["cell_type"] == LteCellType.SERVING)
        # CSV explicitly provides eNodeB and Sector from synthetic constants
        self.assertEqual(serving["enodeb_id"], _SYN_ENODEB)
        self.assertEqual(serving["sector_id"], _SYN_SECTOR)

    def test_state_field_parsed(self):
        rows = _captured_rows(EXTENDED_CSV)
        for row in rows:
            self.assertEqual(row["state"], 1)

    def test_first_seen_from_timestamp(self):
        rows = _captured_rows(EXTENDED_CSV)
        for row in rows:
            self.assertEqual(row["first_seen"].year, 2025)


class SerialSourceColumnTests(SimpleTestCase):
    def test_source_column_ignored(self):
        rows = _captured_rows(SERIAL_SOURCE_CSV)
        # Source column must not leak into model rows
        for row in rows:
            self.assertNotIn("Source", row)
            self.assertNotIn("source", row)

    def test_both_rows_persisted(self):
        rows = _captured_rows(SERIAL_SOURCE_CSV)
        self.assertEqual(len(rows), 2)

    def test_neighbor_pci_distinct(self):
        rows = _captured_rows(SERIAL_SOURCE_CSV)
        neighbor = next(r for r in rows if r["cell_type"] == LteCellType.NEIGHBOR)
        self.assertEqual(neighbor["pci"], _SYN_PCI_SERIAL_NEIGHBOR)


class KeyFieldsTest(SimpleTestCase):
    """Verify that the upsert key_fields include cell_type and pci."""

    def test_key_fields_include_cell_type_and_pci(self):
        captured_kwargs = {}

        def fake_bulk(*, model, key_fields, rows, **kwargs):
            captured_kwargs["key_fields"] = key_fields
            return 0, 0, 0

        with patch(_PATCH_BULK, side_effect=fake_bulk):
            process_lte_wardriving(dataframe=_df(EXTENDED_CSV))

        self.assertIn("cell_type", captured_kwargs["key_fields"])
        self.assertIn("pci", captured_kwargs["key_fields"])


class LteAndroidWrapperTests(SimpleTestCase):
    """
    Smoke tests for process_file_lte_android.

    Verify that the wrapper reads a CSV file from disk and delegates to
    process_lte_wardriving with the expected rows, covering both the
    extended Spanish format and the legacy English format.
    """

    def _run_wrapper(self, csv_text: str) -> list[dict]:
        from apps.process.android import process_file_lte_android

        captured = []

        def fake_bulk(*, model, key_fields, rows, **kwargs):
            captured.extend(rows)
            return len(rows), 0, 0

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(csv_text)
            tmp_path = fh.name

        try:
            with patch(_PATCH_BULK, side_effect=fake_bulk):
                process_file_lte_android(file_path=tmp_path)
        finally:
            os.unlink(tmp_path)

        return captured

    def test_extended_format_two_rows_persisted(self):
        rows = self._run_wrapper(EXTENDED_CSV)
        self.assertEqual(len(rows), 2)

    def test_extended_format_cell_types(self):
        rows = self._run_wrapper(EXTENDED_CSV)
        cell_types = {r["cell_type"] for r in rows}
        self.assertIn(LteCellType.SERVING, cell_types)
        self.assertIn(LteCellType.NEIGHBOR, cell_types)

    def test_extended_format_rf_fields_populated(self):
        rows = self._run_wrapper(EXTENDED_CSV)
        serving = next(r for r in rows if r["cell_type"] == LteCellType.SERVING)
        self.assertEqual(serving["pci"], _SYN_SECTOR)
        self.assertEqual(serving["earfcn"], 2825)
        self.assertAlmostEqual(float(serving["dl_freq_mhz"]), 2627.5)

    def test_legacy_english_format_accepted(self):
        rows = self._run_wrapper(LEGACY_EN_CSV)
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(row["cell_type"], LteCellType.SERVING)

    def test_device_source_propagated(self):
        from apps.process.android import process_file_lte_android
        from apps.wardriving.models import SourceDevice

        captured = []

        def fake_bulk(*, model, key_fields, rows, **kwargs):
            captured.extend(rows)
            return len(rows), 0, 0

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(EXTENDED_CSV)
            tmp_path = fh.name

        try:
            with patch(_PATCH_BULK, side_effect=fake_bulk):
                process_file_lte_android(
                    file_path=tmp_path,
                    device_source=SourceDevice.LTE_ANDROID,
                    uploaded_by="test_user",
                )
        finally:
            os.unlink(tmp_path)

        for row in captured:
            self.assertEqual(row["device_source"], SourceDevice.LTE_ANDROID)
            self.assertEqual(row["uploaded_by"], "test_user")


class MissingFreqFieldsTests(SimpleTestCase):
    """
    Regression tests for the NaN bug: when FreqDL_MHz / FreqUL_MHz are empty
    in the CSV, pandas.to_numeric produces float('nan').  float('nan') or 0
    returns NaN (truthy in Python), which Django's DecimalField rejects with
    '"nan": el valor debe ser un número decimal.'
    """

    def test_row_persisted_when_freq_empty(self):
        rows = _captured_rows(EXTENDED_MISSING_FREQ_CSV)
        self.assertEqual(len(rows), 1)

    def test_dl_freq_defaults_to_zero(self):
        rows = _captured_rows(EXTENDED_MISSING_FREQ_CSV)
        self.assertEqual(float(rows[0]["dl_freq_mhz"]), 0.0)

    def test_ul_freq_defaults_to_zero(self):
        rows = _captured_rows(EXTENDED_MISSING_FREQ_CSV)
        self.assertEqual(float(rows[0]["ul_freq_mhz"]), 0.0)

    def test_other_fields_still_parsed(self):
        rows = _captured_rows(EXTENDED_MISSING_FREQ_CSV)
        row = rows[0]
        self.assertEqual(row["earfcn"], _SYN_EARFCN)
        self.assertEqual(row["pci"], _SYN_PCI)
        self.assertEqual(row["rssi"], -85)
        self.assertEqual(row["rsrp"], -93)
        self.assertEqual(row["rsrq"], -12)
        self.assertEqual(row["sinr"], 8)
