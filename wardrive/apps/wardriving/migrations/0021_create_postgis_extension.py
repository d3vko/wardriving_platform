from django.contrib.postgres.operations import CreateExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "wardriving",
            "0020_ltewardriving_cell_type_ltewardriving_dl_freq_mhz_and_more",
        ),
    ]

    operations = [
        CreateExtension("postgis"),
    ]
