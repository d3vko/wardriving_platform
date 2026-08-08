# Expose denormalized region (ADM1) on map BI views.

import django_db_views.migration_functions
import django_db_views.operations
from django.db import migrations


_WIFI_FORWARD = """SELECT
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
            COALESCE(NULLIF(BTRIM(wardriving.city), ''), 'Unknown') AS city,
            COALESCE(NULLIF(BTRIM(wardriving.region), ''), 'Unknown') AS region,
            COALESCE(wardriving.country, 'Unknown') AS country,
            COALESCE(wardriving.country_iso, 'ZZ') AS country_iso
        FROM wardriving
        LEFT JOIN vendor ON vendor.prefix_oui = wardriving.mac_oui
        WHERE
            (wardriving.current_latitude != 0 AND wardriving.current_longitude != 0)
            AND wardriving.deleted_at IS NULL
            AND wardriving.location IS NOT NULL"""

_WIFI_REVERSE = """SELECT
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
            COALESCE(NULLIF(BTRIM(wardriving.city), ''), 'Unknown') AS city,
            COALESCE(wardriving.country, 'Unknown') AS country,
            COALESCE(wardriving.country_iso, 'ZZ') AS country_iso
        FROM wardriving
        LEFT JOIN vendor ON vendor.prefix_oui = wardriving.mac_oui
        WHERE
            (wardriving.current_latitude != 0 AND wardriving.current_longitude != 0)
            AND wardriving.deleted_at IS NULL
            AND wardriving.location IS NOT NULL"""

_MOBILE_FORWARD = """SELECT
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
            COALESCE(NULLIF(BTRIM(lte.city), ''), 'Unknown') AS city,
            COALESCE(NULLIF(BTRIM(lte.region), ''), 'Unknown') AS region,
            COALESCE(lte.country, 'Unknown') AS country,
            COALESCE(lte.country_iso, 'ZZ') AS country_iso
        FROM lte_wardriving AS lte
        WHERE
            (lte.current_latitude != 0 AND lte.current_longitude != 0)
            AND lte.deleted_at IS NULL
            AND lte.location IS NOT NULL"""

_MOBILE_REVERSE = """SELECT
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
            COALESCE(NULLIF(BTRIM(lte.city), ''), 'Unknown') AS city,
            COALESCE(lte.country, 'Unknown') AS country,
            COALESCE(lte.country_iso, 'ZZ') AS country_iso
        FROM lte_wardriving AS lte
        WHERE
            (lte.current_latitude != 0 AND lte.current_longitude != 0)
            AND lte.deleted_at IS NULL
            AND lte.location IS NOT NULL"""


class Migration(migrations.Migration):

    dependencies = [
        ("misc", "0007_denormalized_geos_labels_views"),
        ("wardriving", "0025_ltewardriving_region_wardriving_region"),
    ]

    operations = [
        django_db_views.operations.ViewRunPython(
            code=django_db_views.migration_functions.ForwardViewMigration(
                _WIFI_FORWARD,
                "wardriving_vendor",
                engine="django.contrib.gis.db.backends.postgis",
            ),
            reverse_code=django_db_views.migration_functions.BackwardViewMigration(
                _WIFI_REVERSE,
                "wardriving_vendor",
                engine="django.contrib.gis.db.backends.postgis",
            ),
            atomic=False,
        ),
        django_db_views.operations.ViewRunPython(
            code=django_db_views.migration_functions.ForwardViewMigration(
                _MOBILE_FORWARD,
                "wardriving_mobile",
                engine="django.contrib.gis.db.backends.postgis",
            ),
            reverse_code=django_db_views.migration_functions.BackwardViewMigration(
                _MOBILE_REVERSE,
                "wardriving_mobile",
                engine="django.contrib.gis.db.backends.postgis",
            ),
            atomic=False,
        ),
    ]
