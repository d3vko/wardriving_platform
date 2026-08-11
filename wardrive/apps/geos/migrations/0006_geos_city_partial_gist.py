"""
GiST parciales sobre geos_city.polygon por admin_level vivo.

Acelera los LEFT JOIN LATERAL de geos_labels.resolve_geos_labels_for_ids
(admin_level = N AND deleted_at IS NULL + bbox &&), que eran el cuello de botella
del ingest síncrono. El matching sigue siendo set-based; estos índices acotan el
scan espacial a las filas vivas del nivel correcto.
"""

from django.contrib.postgres.indexes import GistIndex
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("geos", "0005_alter_city_admin_level"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="city",
            index=GistIndex(
                condition=models.Q(
                    ("admin_level", 0), ("deleted_at__isnull", True)
                ),
                fields=["polygon"],
                name="geos_city_gist_adm0_alive",
            ),
        ),
        migrations.AddIndex(
            model_name="city",
            index=GistIndex(
                condition=models.Q(
                    ("admin_level", 1), ("deleted_at__isnull", True)
                ),
                fields=["polygon"],
                name="geos_city_gist_adm1_alive",
            ),
        ),
        migrations.AddIndex(
            model_name="city",
            index=GistIndex(
                condition=models.Q(
                    ("admin_level", 2), ("deleted_at__isnull", True)
                ),
                fields=["polygon"],
                name="geos_city_gist_adm2_alive",
            ),
        ),
        migrations.AddIndex(
            model_name="city",
            index=GistIndex(
                condition=models.Q(
                    ("admin_level", 3), ("deleted_at__isnull", True)
                ),
                fields=["polygon"],
                name="geos_city_gist_adm3_alive",
            ),
        ),
    ]
