class WardrivingVendorsSQL:
    view_definition = {
        "django.db.backends.postgresql": r"""
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
            wardriving.accuracy_meters
        FROM wardriving
        LEFT JOIN vendor ON vendor.prefix_oui = wardriving.mac_oui
        WHERE
            (wardriving.current_latitude!=0 AND wardriving.current_longitude!=0)
            AND wardriving.deleted_at is NULL
        """,
        # 🚧 TODO: All other db systems
        "django.db.backends.sqlite3": "SELECT 1 AS id WHERE 1=0",
        "django.db.backends.mysql": "SELECT 1 AS id WHERE 1=0",
    }
