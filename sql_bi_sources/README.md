# sql_bi_sources

Canonical native SQL for Metabase dashboard **DB00 - Wardriving**. Edit here first; Metabase is the destination.

## Layout

| Path | View | Domain |
|------|------|--------|
| [`wardriving_normal/`](wardriving_normal/) | `wardriving_vendor` | WiFi / BLE |
| [`wardriving_movil/`](wardriving_movil/) | `wardriving_mobile` | LTE |
| [`_legacy/`](_legacy/) | historical | kept for reference only |

Views are defined in Django: [`wardrive/apps/misc/sql_views.py`](../wardrive/apps/misc/sql_views.py) (migrations under `wardrive/apps/misc/`).

Each file starts with comments:

```sql
-- Metabase display: map | table | row | pie | ...
-- View: wardriving_vendor | wardriving_mobile
-- D0x - title
```

## D00–D08

| Code | WiFi/BLE | LTE | Typical display |
|------|----------|-----|-----------------|
| D00 | Map | Map | map (pin) |
| D01 | Detail table | Detail table | table |
| D02 | Qty by auth type | Qty by cell type | row |
| D03 | Qty by device | Qty by device | row |
| D04 | Qty by author | — (no LTE mirror) | row |
| D05 | Qty by signal strength | Qty by signal strength | pie |
| D06 | Qty by vendor | Qty by provider | row / pie |
| D07 | Qty by channel | Qty by band | row |
| D08 | Qty by geo | Qty by geo | pie |

## Field filters (`{{tags}}`)

Placeholders in `WHERE` must stay **Metabase field filters** (`type: dimension`), not `type: text`.

### WiFi (`wardriving_vendor`)

| Tag | Column | widget-type |
|-----|--------|-------------|
| `ssid` | ssid | `string/=` |
| `device_source` | device_source | `string/=` |
| `first_seen` | first_seen | `date/all-options` |
| `bssid` | mac | `string/contains` |
| `auth_mode` | auth_mode | `string/=` |
| `vendor` | vendor | `string/=` |
| `signal_streng` | signal_streng | `string/=` |
| `city` / `country` / `country_iso` | same | `string/=` |

### LTE (`wardriving_mobile`)

| Tag | Column | widget-type |
|-----|--------|-------------|
| `band` | band | `string/=` |
| `provider` | provider | `string/=` |
| `device_source` | device_source | `string/=` |
| `tech` | tech | `string/=` |
| `first_seen` | first_seen | `date/all-options` |
| `cell_type` | cell_type | `string/=` |
| `signal_streng` | signal_streng | `string/=` |
| `city` / `country` / `country_iso` | same | `string/=` |

Do **not** rename the DB column `signal_streng`.

## Dashboard DB00

- Tabs: **WIFI/BLE**, **LTE**
- Shared filters: First Seen, City, Country, Country ISO, Signal Strength
- WiFi-only: SSID, Device Source, BSSID/MAC, Auth Mode, Vendor
- LTE-only: Band, Mobile Provider, Mobile Device Source, Mobile Tech, Cell Type

Dashboard `parameter_mappings` target `["dimension", ["template-tag", "<name>"]]` by tag **name**.

## Anti-patterns

- Do **not** rewrite these cards with MCP `construct_native_query` / `update_question` for the native SQL body — those APIs degrade field filters to `type: text` and break dashboard filters.
- To change SQL or restore filters: keep `{{...}}` names, then set `template-tags` as `dimension` via Metabase REST/`report_card` (see project skill).

## Replica / fresh host

Use the Cursor skill **`metabase-wardriving-bi`** (`.cursor/skills/metabase-wardriving-bi/` and personal copy under `~/.cursor/skills/`).

Demo screenshots of DB00: [`../demos/README.md`](../demos/README.md).
