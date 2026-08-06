# demos/

Screenshots for README and ops docs. Prefer these **local paths** over external raw GitHub URLs.

## Legacy BI previews

| File | Description |
|------|-------------|
| [`map.png`](map.png) | Map-style BI preview (legacy) |
| [`table_and_more_analysis.png`](table_and_more_analysis.png) | Table + aggregations (legacy) |
| [`analysis_per_participant.png`](analysis_per_participant.png) | Per-participant / signal analysis (legacy) |

## DB00 — Wardriving (Metabase)

Dashboard tabs **WIFI/BLE** and **LTE**, collection *Wardriving Activity*. Canonical SQL: [`../sql_bi_sources/`](../sql_bi_sources/).

| File | Description |
|------|-------------|
| [`db00-wifi-map-and-table.png`](db00-wifi-map-and-table.png) | WIFI/BLE: D00 map + D01 detail table |
| [`db00-wifi-charts-channel-device-signal.png`](db00-wifi-charts-channel-device-signal.png) | WIFI/BLE: D07 channel, D03 device, D05 signal |
| [`db00-wifi-charts-auth-vendor.png`](db00-wifi-charts-auth-vendor.png) | WIFI/BLE: D02 auth, D06 vendor, D08 geo |
| [`db00-wifi-geo-and-author.png`](db00-wifi-geo-and-author.png) | WIFI/BLE: D08 geo + D04 author |
| [`db00-lte-map.png`](db00-lte-map.png) | LTE: D00 map + LTE filters |
| [`db00-lte-map-and-table.png`](db00-lte-map-and-table.png) | LTE: D00 map + D01 detail table |

## Metabase UI extras

| File | Description |
|------|-------------|
| [`metabase-geos-city-filter.png`](metabase-geos-city-filter.png) | Field-filter UI on geo metadata |
| [`metabase-map-pin-detail.png`](metabase-map-pin-detail.png) | Map visualization / pin detail |
| [`metabase-map-view-alt.png`](metabase-map-view-alt.png) | Alternate map view |
| [`metabase-map-view-alt2.png`](metabase-map-view-alt2.png) | Alternate map view |

> Screenshots may show event/sample geography from a live instance. For synthetic GPS values in tests and fixtures, follow the project convention (no real coordinates).
