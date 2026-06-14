"""
Unit tests for process_lte_wardriving (apps.process.rf).

Covers:
  - Legacy ES/EN CSV (15 columns, no TipoCelda/eNodeB/PCI/EARFCN)
  - Extended firmware/serial CSV (23 columns, serving + neighbor rows)
  - Serial WebSerial export with leading "Source" column
  - Placeholder rows are filtered (CellID sentinel, LAC sentinel, MCC=0, no GPS)
  - Timestamp column drives first_seen (not now())
  - eNodeB / sector_id derived from cell_id when absent

Data policy: all CSV fixtures below use SYNTHETIC data — no real GPS captures,
no real cell IDs from field sessions.  See .cursor/skills/wardriving-test-data-policy/SKILL.md.
"""

import io
from datetime import datetime, timezone
from unittest.mock import patch

from django.test import SimpleTestCase
from pandas import read_csv

from apps.process.rf import process_lte_wardriving
from apps.wardriving import LteCellType

_PATCH_BULK = "apps.process.rf.bulk_upsert_by_keys"


def _df(csv_text: str):
    return read_csv(io.StringIO(csv_text), sep=",", low_memory=False)


# ---------------------------------------------------------------------------
# Legacy format (15-column English, as produced by Android / old firmware)
# ---------------------------------------------------------------------------

LEGACY_EN_CSV = """\
Timestamp,Technology,State,MCC,MNC,LAC,CellID,Band,RSSI,RSRP,RSRQ,SINR,Operator,Longitude,Latitude
2025-06-14 15:00:01,LTE,1,334,20,581,40918550,7,-106,-106,-8,0,TELCEL,-99.1332,19.4326
1970-01-01 03:27:06,LTE,0,000,00,65535,268435455,,-106,-106,-7,0,TELCEL,,
2025-06-14 15:00:02,LTE,1,334,20,581,40918551,7,-100,-100,-7,2,TELCEL,-99.1332,19.4326
"""

# Legacy Spanish (RF firmware)
LEGACY_ES_CSV = """\
Timestamp,Tecnología,Estado,MCC,MNC,LAC,CellID,Banda,RSSI,RSRP,RSRQ,SINR,Operador,Longitud,Latitud
2025-06-14 15:00:03,LTE,1,334,20,581,40918552,7,-103,-103,-9,0,TELCEL,-99.1332,19.4326
"""

# Extended firmware schema with serving + neighbor rows
EXTENDED_CSV = """\
Timestamp,Tecnología,TipoCelda,Estado,MCC,MNC,LAC,CellID,eNodeB,Sector,PCI,Banda,EARFCN,FreqDL_MHz,FreqUL_MHz,RSSI,RSRP,RSRQ,SINR,Operador,Longitud,Latitud
2025-06-14 15:00:05,LTE,serving,1,334,20,12345,39485461,154240,21,21,7,2825,2627.5,2507.5,-85,-93,-12,8,Telcel,-99.1332,19.4326
2025-06-14 15:00:05,LTE,neighbor,1,334,20,12345,0,0,0,23,7,2825,2627.5,2507.5,0,-91,-11,0,Telcel,-99.1332,19.4326
"""

# Serial WebSerial export — identical to extended but prefixed with Source column
SERIAL_SOURCE_CSV = """\
Source,Timestamp,Tecnología,TipoCelda,Estado,MCC,MNC,LAC,CellID,eNodeB,Sector,PCI,Banda,EARFCN,FreqDL_MHz,FreqUL_MHz,RSSI,RSRP,RSRQ,SINR,Operador,Longitud,Latitud
lte,2025-06-14 15:00:10,LTE,serving,1,334,20,99999,390,15,11,4,7,2825,2627.5,2507.5,-80,-88,-10,5,Telcel,-99.1332,19.4326
lte,2025-06-14 15:00:10,LTE,neighbor,1,334,20,99999,0,0,0,44,7,2825,2627.5,2507.5,0,-95,-13,0,Telcel,-99.1332,19.4326
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
        self.assertEqual(rows[0]["provider"], "TELCEL")


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
        self.assertEqual(serving["pci"], 21)
        self.assertEqual(serving["earfcn"], 2825)

    def test_freq_fields_populated(self):
        rows = _captured_rows(EXTENDED_CSV)
        serving = next(r for r in rows if r["cell_type"] == LteCellType.SERVING)
        self.assertAlmostEqual(float(serving["dl_freq_mhz"]), 2627.5)
        self.assertAlmostEqual(float(serving["ul_freq_mhz"]), 2507.5)

    def test_enodeb_sector_from_csv(self):
        rows = _captured_rows(EXTENDED_CSV)
        serving = next(r for r in rows if r["cell_type"] == LteCellType.SERVING)
        # CSV explicitly provides eNodeB=154240, Sector=21
        self.assertEqual(serving["enodeb_id"], 154240)
        self.assertEqual(serving["sector_id"], 21)

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
        self.assertEqual(neighbor["pci"], 44)


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
