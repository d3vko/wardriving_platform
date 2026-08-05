import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("wardriving", "0021_create_postgis_extension"),
    ]

    operations = [
        migrations.AddField(
            model_name="wardriving",
            name="location",
            field=django.contrib.gis.db.models.fields.PointField(
                blank=True,
                null=True,
                srid=4326,
                verbose_name="Location (WGS84)",
            ),
        ),
        migrations.AddField(
            model_name="ltewardriving",
            name="location",
            field=django.contrib.gis.db.models.fields.PointField(
                blank=True,
                null=True,
                srid=4326,
                verbose_name="Location (WGS84)",
            ),
        ),
    ]
