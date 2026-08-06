---
name: metabase-wardriving-bi
description: >-
  Configures and replicates Metabase DB00 Wardriving BI (sql_bi_sources native
  questions, wardriving_vendor/mobile views, dimension field filters, dashboard
  tabs WIFI/BLE and LTE). Use when restoring field filters, pushing SQL to
  Metabase, recreating DB00 on a fresh host, or editing sql_bi_sources.
---

# Metabase Wardriving BI (DB00)

## When to use

- Restore or create native questions from `sql_bi_sources/`
- Fix dashboard filters after a broken MCP SQL push
- Fresh-install Metabase BI on another host
- Add dashboard heading/text cards or parameter mappings

## Hard rules

1. **SQL source of truth:** `sql_bi_sources/wardriving_normal/` (WiFi) and `sql_bi_sources/wardriving_movil/` (LTE).
2. **Never** use MCP `construct_native_query` / `update_question` to rewrite these native cards — they collapse template-tags to `type: text` and break DB00 filters.
3. Field filters must be `type: "dimension"` with `widget-type` + `dimension` pointing at the view column. Prefer portable field refs by table/column name when the API supports them; otherwise resolve `metabase_field.id` after sync.
4. Do not rename DB column `signal_streng`.
5. Orchestration in this repo uses **`podman-compose`**, not docker compose.

## Fresh install checklist

### 1. App data + views

1. Run app migrations so views `wardriving_vendor` and `wardriving_mobile` exist (definitions in `wardrive/apps/misc/sql_views.py`).
2. In Metabase, add/connect the app Postgres DB and **Sync database schema**.
3. Confirm tables/views appear; note table ids if needed for field lookup.

### 2. Create questions

For each `D0x - *.sql` file:

1. Create a native question in collection **Wardriving Activity** (or equivalent).
2. Paste SQL **unchanged** (keep `{{tags}}`).
3. Set display from the file header comment (`map`, `table`, `row`, `pie`, …).
4. For **every** `{{tag}}`, configure a **Field Filter** (dimension), not a text variable. Map using the tables in `sql_bi_sources/README.md`.
5. Dashboard-facing parameters: string filters use search + multi-select where the product UI allows; `first_seen` → `date/all-options`; WiFi `bssid` → `string/contains` on `mac`.

### 3. Dashboard DB00

1. Create dashboard **DB00 - Wardriving** with tabs **WIFI/BLE** and **LTE**.
2. Add WiFi cards to WIFI/BLE, LTE cards to LTE (LTE has no D04 author chart).
3. Create dashboard parameters (shared + WiFi-only + LTE-only) matching README.
4. For each dashcard, map parameters to `["dimension", ["template-tag", "<name>"]]` (same tag **names** as in SQL).
5. Optional: virtual heading/text dashcards (`card_id` null, `visualization_settings.virtual_card.display` = `heading`|`text`) — MCP `update_dashboard` cannot create these; use REST or app DB `report_dashboardcard`.

### 4. Verify

- `read_resource` / card inspect: all template-tags `type: dimension` with `widget-type`.
- Applying SSID / Band / Signal Strength on DB00 must not error about missing field filters.
- LTE cards include `{{signal_streng}}` and dashboard **Band** + **Signal Strength** mappings.

## Safe update pattern (existing cards)

1. Change SQL only in `sql_bi_sources/`.
2. Copy native SQL into Metabase while **preserving** existing dimension template-tag definitions (REST `PUT /api/card/{id}` or careful `report_card.dataset_query` update).
3. If tags were degraded to text: rebuild the dimension map from README (do not re-run `construct_native_query`).
4. Re-check `report_dashboardcard.parameter_mappings` by tag name.

## Tag maps (canonical names)

**WiFi** `wardriving_vendor`: `ssid`, `device_source`, `first_seen`, `bssid`→`mac`, `auth_mode`, `vendor`, `signal_streng`, `city`, `country`, `country_iso`.

**LTE** `wardriving_mobile`: `band`, `provider`, `device_source`, `tech`, `first_seen`, `cell_type`, `signal_streng`, `city`, `country`, `country_iso`.

Host-specific field ids change after sync — rediscover by `(table.name, field.name)`. See optional `reference.md` for one host snapshot.

## Anti-patterns

- Inventing LTE filters for SSID/BSSID.
- Mixing WiFi and LTE template-tag sets on the wrong view.
- Committing Metabase API keys / session tokens.
