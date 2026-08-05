from django.db import migrations

# Solo coords WGS84 válidas y no-placeholder (0,0). lat/lon Decimal intactos.
_BACKFILL_SQL = """
UPDATE {table}
SET location = ST_SetSRID(
    ST_MakePoint(current_longitude::double precision, current_latitude::double precision),
    4326
)
WHERE current_latitude IS NOT NULL
  AND current_longitude IS NOT NULL
  AND NOT (current_latitude = 0 AND current_longitude = 0)
  AND current_latitude BETWEEN -90 AND 90
  AND current_longitude BETWEEN -180 AND 180;
"""

_REVERSE_SQL = "UPDATE {table} SET location = NULL;"


class Migration(migrations.Migration):

    dependencies = [
        ("wardriving", "0022_wardriving_ltewardriving_location"),
    ]

    operations = [
        migrations.RunSQL(
            sql=_BACKFILL_SQL.format(table="wardriving"),
            reverse_sql=_REVERSE_SQL.format(table="wardriving"),
        ),
        migrations.RunSQL(
            sql=_BACKFILL_SQL.format(table="lte_wardriving"),
            reverse_sql=_REVERSE_SQL.format(table="lte_wardriving"),
        ),
    ]
