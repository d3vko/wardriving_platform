# Generated manually for ADM hierarchy (region + admin_level 0/1/2)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("geos", "0002_city_admin_level_alter_city_city_alter_city_source_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="city",
            name="region",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Nombre ADM1 (estado/provincia); vacío para filas ADM0/ADM2.",
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="city",
            name="admin_level",
            field=models.PositiveSmallIntegerField(
                db_index=True,
                default=2,
                help_text=(
                    "0 = país (ADM0), 1 = estado/provincia (ADM1), "
                    "2 = municipio (ADM2)."
                ),
            ),
        ),
        migrations.AlterField(
            model_name="city",
            name="city",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Nombre ADM2; vacío para filas ADM0/ADM1.",
                max_length=255,
            ),
        ),
        migrations.AddIndex(
            model_name="city",
            index=models.Index(
                fields=["country_iso", "region", "city"],
                name="geos_city_country_5f1a2b_idx",
            ),
        ),
    ]
