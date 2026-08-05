from django.contrib.gis.db import models

from apps.core.models import BaseModel


class City(BaseModel):
    """Extensión urbana (built-up / Urban Centre), no límite administrativo municipal."""

    city = models.CharField(max_length=255, db_index=True)
    country = models.CharField(max_length=128, db_index=True)
    country_iso = models.CharField(
        max_length=2,
        db_index=True,
        help_text="ISO 3166-1 alpha-2 (US, MX, BR, ...)",
    )
    polygon = models.MultiPolygonField(srid=4326)

    # Idempotencia del seed
    source = models.CharField(max_length=32, default="ghs_ucdb")
    source_id = models.CharField(max_length=64, db_index=True)

    class Meta:
        db_table = "geos_city"
        verbose_name = "City"
        verbose_name_plural = "Cities"
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_id"],
                name="uniq_geos_city_source_id",
            ),
        ]
        indexes = [
            models.Index(fields=["country_iso", "city"]),
        ]

    def __str__(self):
        return f"{self.city}, {self.country} ({self.country_iso})"
