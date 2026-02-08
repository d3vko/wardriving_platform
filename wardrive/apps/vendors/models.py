from django.db import models
from django.utils.timezone import now

from decimal import Decimal, InvalidOperation

from . import SourceVendor
from apps.core.models import BaseModel


class Vendors(BaseModel):
    # e.g. "MA-L" (24-bit), "MA-M" (28-bit), "MA-S" (36-bit), "IAB", etc.
    registry = models.CharField(max_length=8, db_index=True)
    # Prefix HEX: "F4BD9E"
    assignment = models.CharField(max_length=12, db_index=True)
    # Length expressed in bits (24, 28, 36...). e.g. MA-L -> 24.
    prefix_bits = models.PositiveSmallIntegerField(db_index=True)
    organization_name = models.CharField(max_length=255, db_index=True)
    organization_address = models.TextField(blank=True, default="")
    # Field “normalized for search
    normalized_prefix = models.CharField(max_length=12, db_index=True)
    # Trace for source
    source = models.CharField(max_length=64, choices=SourceVendor.CHOICES)
    source_url = models.URLField(blank=True, default="")
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["registry", "prefix_bits", "normalized_prefix"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "registry",
                    "assignment",
                    "organization_name",
                    "organization_address",
                ],
                name="uniq_registry_assignment_org_addr",
            )
        ]
        db_table = "vendor"
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"

    def __str__(self):
        return f"{self.pk} - {self.assignment} with registry {self.registry} ({self.prefix_bits} bits)"
