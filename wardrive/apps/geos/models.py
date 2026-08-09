from django.contrib.gis.db import models

from apps.core.models import BaseModel


class City(BaseModel):
    """Polígono administrativo: país (ADM0), región (ADM1) o municipio (ADM2)."""

    city = models.CharField(
        max_length=255,
        db_index=True,
        blank=True,
        default="",
        help_text="Nombre ADM2; vacío para filas ADM0/ADM1.",
    )
    region = models.CharField(
        max_length=255,
        db_index=True,
        blank=True,
        default="",
        help_text="Nombre ADM1 (estado/provincia); vacío para filas ADM0/ADM2.",
    )
    country = models.CharField(max_length=128, db_index=True)
    country_iso = models.CharField(
        max_length=2,
        db_index=True,
        help_text="ISO 3166-1 alpha-2 (US, MX, BR, ...)",
    )
    admin_level = models.PositiveSmallIntegerField(
        db_index=True,
        default=2,
        help_text=(
            "0 = país (ADM0), 1 = estado/provincia (ADM1), "
            "2 = municipio (ADM2), 3 = localidad/centroide buffered."
        ),
    )
    polygon = models.MultiPolygonField(srid=4326)

    # Idempotencia del seed
    source = models.CharField(max_length=32, default="geoboundaries")
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
            models.Index(fields=["country_iso", "region", "city"]),
            models.Index(fields=["admin_level", "country_iso"]),
        ]

    def __str__(self):
        if self.city:
            if self.region:
                return (
                    f"{self.city}, {self.region}, {self.country} ({self.country_iso})"
                )
            return f"{self.city}, {self.country} ({self.country_iso})"
        if self.region:
            return f"{self.region}, {self.country} ({self.country_iso})"
        return f"{self.country} ({self.country_iso}) ADM{self.admin_level}"
