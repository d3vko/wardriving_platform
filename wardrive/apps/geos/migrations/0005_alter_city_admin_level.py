# Generated manually: ADM3 localidades (centroides buffered) + labels KNN.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("geos", "0004_rename_geos_city_region_index"),
    ]

    operations = [
        migrations.AlterField(
            model_name="city",
            name="admin_level",
            field=models.PositiveSmallIntegerField(
                db_index=True,
                default=2,
                help_text=(
                    "0 = país (ADM0), 1 = estado/provincia (ADM1), "
                    "2 = municipio (ADM2), 3 = localidad/centroide buffered."
                ),
            ),
        ),
    ]
