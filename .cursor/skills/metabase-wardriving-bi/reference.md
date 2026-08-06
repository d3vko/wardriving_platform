# Host-specific Metabase field ids (snapshot)

**Host:** wardriving-ctf.rf-village-mx.com (app DB synced into Metabase).  
**Not portable.** On a fresh install, re-resolve ids by view + column name after schema sync.

## Tables

| View | Typical table_id (this host) |
|------|------------------------------|
| `wardriving_vendor` | 146 |
| `wardriving_mobile` | 3309 |

## WiFi fields (`wardriving_vendor`)

| Column | field id |
|--------|----------|
| mac | 1425 |
| vendor | 1427 |
| ssid | 1429 |
| auth_mode | 1430 |
| first_seen | 1431 |
| signal_streng | 1434 |
| device_source | 1435 |
| city | 91008 |
| country | 91009 |
| country_iso | 91010 |

## LTE fields (`wardriving_mobile`)

| Column | field id |
|--------|----------|
| cell_type | 90984 |
| band | 90989 |
| signal_streng | 90997 |
| provider | 90998 |
| tech | 90999 |
| first_seen | 91000 |
| device_source | 91001 |
| city | 91005 |
| country | 91006 |
| country_iso | 91007 |

## Dashboard DB00 parameter ids (this host)

| Name | id | Notes |
|------|-----|--------|
| First Seen | `db4f10aa` | shared |
| SSID | `29766fa6` | WiFi |
| Device Source | `728681f2` | WiFi |
| BSSID/MAC | `d893a638` | WiFi |
| Auth Mode | `73b2af1e` | WiFi |
| Vendor | `fd469564` | WiFi |
| Signal Strength | `c1363276` | shared (WiFi + LTE) |
| Band | `f8e2a91c` | LTE |
| Mobile Provider | `14b46b3f` | LTE |
| Mobile Device Source | `b5e69d92` | LTE |
| Mobile Tech | `7af15f4` | LTE |
| Cell Type | `ab6dfa25` | LTE |
| City / Country / Country ISO | `600eb875` / `bf3223e` / `b5cbe2bb` | shared |

## Card id map (this host, indicative)

WiFi: 47 D00, 39 D01, 40 D02, 41 D03, 42 D04, 43 D05, 44 D06, 49 D07, 50 D08  
LTE: 45 D00, 48 D01, 51 D02, 55 D03, 52 D05, 54 D06, 56 D07, 53 D08
