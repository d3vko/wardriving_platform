_WIFI_VENDOR_PG = r"""
        SELECT
            wardriving.id,
            wardriving.mac,
            COALESCE(vendor.registry, 'Not setted yet') AS registry,
            COALESCE(vendor.organization_name, 'Not found yet') AS vendor,
            COALESCE(vendor.source, 'Not provided yet') AS source,
            wardriving.ssid,
            wardriving.auth_mode,
            wardriving.first_seen,
            wardriving.channel,
            wardriving.rssi,
            CASE
                WHEN wardriving.rssi > -50 THEN 'Excellent'
                WHEN wardriving.rssi BETWEEN -60 AND -50 THEN 'Good'
                WHEN wardriving.rssi BETWEEN -70 AND -60 THEN 'Fair'
                ELSE 'Weak'
            END AS signal_streng,
            wardriving.device_source,
            wardriving.uploaded_by,
            wardriving.type,
            wardriving.current_latitude,
            wardriving.current_longitude,
            wardriving.altitude_meters,
            wardriving.accuracy_meters,
            COALESCE(NULLIF(BTRIM(city.city), ''), 'Unknown') AS city,
            COALESCE(city.country, 'Unknown') AS country,
            COALESCE(city.country_iso, 'ZZ') AS country_iso
        FROM wardriving
        LEFT JOIN vendor ON vendor.prefix_oui = wardriving.mac_oui
        LEFT JOIN LATERAL (
            SELECT gc.city, gc.country, gc.country_iso
            FROM geos_city gc
            WHERE gc.deleted_at IS NULL
                AND gc.polygon && wardriving.location
                AND ST_Intersects(gc.polygon, wardriving.location)
            ORDER BY gc.admin_level DESC, ST_Area(gc.polygon::geography) ASC
            LIMIT 1
        ) AS city ON TRUE
        WHERE
            (wardriving.current_latitude != 0 AND wardriving.current_longitude != 0)
            AND wardriving.deleted_at IS NULL
            AND wardriving.location IS NOT NULL
        """

_MOBILE_PG = r"""
        SELECT
            lte.id,
            lte.mcc,
            lte.mnc,
            lte.lac,
            lte.cell_id,
            lte.cell_type,
            lte.state,
            lte.enodeb_id,
            lte.sector_id,
            lte.pci,
            lte.band,
            lte.earfcn,
            lte.dl_freq_mhz,
            lte.ul_freq_mhz,
            lte.rssi,
            lte.rsrp,
            lte.rsrq,
            lte.sinr,
            CASE
                WHEN lte.rssi > -50 THEN 'Excellent'
                WHEN lte.rssi BETWEEN -60 AND -50 THEN 'Good'
                WHEN lte.rssi BETWEEN -70 AND -60 THEN 'Fair'
                ELSE 'Weak'
            END AS signal_streng,
            lte.provider,
            lte.tech,
            lte.first_seen,
            lte.device_source,
            lte.uploaded_by,
            lte.current_latitude,
            lte.current_longitude,
            COALESCE(NULLIF(BTRIM(city.city), ''), 'Unknown') AS city,
            COALESCE(city.country, 'Unknown') AS country,
            COALESCE(city.country_iso, 'ZZ') AS country_iso
        FROM lte_wardriving AS lte
        LEFT JOIN LATERAL (
            SELECT gc.city, gc.country, gc.country_iso
            FROM geos_city gc
            WHERE gc.deleted_at IS NULL
                AND gc.polygon && lte.location
                AND ST_Intersects(gc.polygon, lte.location)
            ORDER BY gc.admin_level DESC, ST_Area(gc.polygon::geography) ASC
            LIMIT 1
        ) AS city ON TRUE
        WHERE
            (lte.current_latitude != 0 AND lte.current_longitude != 0)
            AND lte.deleted_at IS NULL
            AND lte.location IS NOT NULL
        """


class WardrivingVendorsSQL:
    view_definition = {
        # PostGIS is the runtime engine; keep postgresql key for non-GIS envs.
        "django.contrib.gis.db.backends.postgis": _WIFI_VENDOR_PG,
        "django.db.backends.postgresql": _WIFI_VENDOR_PG,
        # 🚧 TODO: All other db systems
        "django.db.backends.sqlite3": "SELECT 1 AS id WHERE 1=0",
        "django.db.backends.mysql": "SELECT 1 AS id WHERE 1=0",
    }


class WardrivingMobileSQL:
    view_definition = {
        "django.contrib.gis.db.backends.postgis": _MOBILE_PG,
        "django.db.backends.postgresql": _MOBILE_PG,
        # 🚧 TODO: All other db systems
        "django.db.backends.sqlite3": "SELECT 1 AS id WHERE 1=0",
        "django.db.backends.mysql": "SELECT 1 AS id WHERE 1=0",
    }
