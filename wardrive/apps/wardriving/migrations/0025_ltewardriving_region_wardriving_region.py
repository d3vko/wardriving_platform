# Generated manually for denormalized ADM1 region on WiFi/LTE captures

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wardriving", "0024_ltewardriving_city_ltewardriving_country_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="ltewardriving",
            name="region",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                verbose_name="Region / ADM1 (denormalized)",
            ),
        ),
        migrations.AddField(
            model_name="wardriving",
            name="region",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                verbose_name="Region / ADM1 (denormalized)",
            ),
        ),
        migrations.AddIndex(
            model_name="ltewardriving",
            index=models.Index(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=["country_iso", "region", "city"],
                name="lte_geo_region_alv",
            ),
        ),
        migrations.AddIndex(
            model_name="wardriving",
            index=models.Index(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=["country_iso", "region", "city"],
                name="wardriving_geo_region_alv",
            ),
        ),
    ]
