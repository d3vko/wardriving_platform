from django.db import models
from django.db.models import Q
from django.utils.timezone import now

from decimal import Decimal, InvalidOperation

from apps.core.models import WardriveBaseModel, SourceDevice


class Wardriving(WardriveBaseModel):
    mac = models.CharField(
        max_length=17, verbose_name="MAC Address", default="AA:BB:CC:DD:EE:FF"
    )  # Format: XX:XX:XX:XX:XX:XX
    ssid = models.CharField(max_length=255, verbose_name="SSID", default="")
    auth_mode = models.CharField(
        max_length=50, verbose_name="Authentication Mode", default=""
    )
    channel = models.IntegerField(verbose_name="Channel")
    rssi = models.IntegerField(verbose_name="RSSI (Signal Strength)")
    current_latitude = models.DecimalField(
        max_digits=13, decimal_places=7, verbose_name="Latitude", default=0
    )
    current_longitude = models.DecimalField(
        max_digits=13, decimal_places=7, verbose_name="Longitude", default=0
    )
    altitude_meters = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Altitude (Meters)",
        default=0,
    )
    accuracy_meters = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="Accuracy (Meters)", default=0
    )
    type = models.CharField(max_length=50, verbose_name="Type", default="WIFI")

    class Meta:
        db_table = "wardriving"
        verbose_name = "Wardriving Data"
        verbose_name_plural = "Wardriving Data"
        indexes = [
            models.Index(
                fields=["uploaded_by", "mac", "channel"],
                name="wardriving_up_mac_ch_alv",
                condition=Q(deleted_at__isnull=True),
            ),
        ]

    def __str__(self):
        device = self.ssid or self.type or "Unknown Device"
        return f"{device} ({self.mac})"

    def is_default_data(self):
        # Check current_latitude / current_longitude
        lat = getattr(self, "current_latitude", None)
        lon = getattr(self, "current_longitude", None)

        def is_zero_or_none(x):
            if x is None:
                return True
            try:
                return Decimal(x) == 0
            except (InvalidOperation, TypeError):
                # Invalid/weird string, NaN, etc. treat as default
                return True

        # Default when we have no real coordinates
        return is_zero_or_none(lat) and is_zero_or_none(lon)


class LTEWardriving(WardriveBaseModel):
    # From csv device content file
    mcc = models.IntegerField(verbose_name="MCC (Mobile Country Code)")
    mnc = models.IntegerField(verbose_name="MNC (Mobile Network Code)")
    lac = models.IntegerField(verbose_name="LAC (Location Area Code)")
    cell_id = models.IntegerField(verbose_name="Cell ID (Cell Global Identity)")
    band = models.TextField(verbose_name="Band")
    rssi = models.IntegerField(verbose_name="RSSI (Signal Strength)")
    rsrp = models.IntegerField(verbose_name="RSRP (Reference Signal Received Power)")
    rsrq = models.IntegerField(verbose_name="RSRQ (Reference Signal Received Quality)")
    sinr = models.IntegerField(
        verbose_name="SINR (Signal-to-Interference-plus-Noise Ratio)"
    )
    provider = models.TextField(verbose_name="Provider", default="")
    current_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, verbose_name="Latitude", default=0
    )
    current_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, verbose_name="Longitude", default=0
    )
    tech = models.TextField(verbose_name="Technology", default="LTE")

    class Meta:
        db_table = "lte_wardriving"
        verbose_name = "LTE Wardriving Found"
        verbose_name_plural = "LTE Wardriving Founds"

    def __str__(self):
        return f"`{self.pk}`:{self.mcc}-{self.mnc}-{self.lac} : ({self.cell_id})"

    def is_default_data(self):
        # Check current_latitude / current_longitude
        lat = getattr(self, "current_latitude", None)
        lon = getattr(self, "current_longitude", None)

        def is_zero_or_none(x):
            if x is None:
                return True
            try:
                return Decimal(x) == 0
            except (InvalidOperation, TypeError):
                # Invalid/weird string, NaN, etc. treat as default
                return True

        # Default when we have no real coordinates
        return is_zero_or_none(lat) and is_zero_or_none(lon)
