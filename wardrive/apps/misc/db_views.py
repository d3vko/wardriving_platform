from django.db import models
from django_db_views.db_view import DBView

from apps.misc.sql_views import (
    WardrivingVendorsSQL,
)


class WardrivingVendorView(DBView):
    id = models.BigIntegerField(primary_key=True)
    mac = models.CharField()
    registry = models.CharField()
    vendor = models.CharField()
    source = models.CharField()
    ssid = models.CharField()
    auth_mode = models.CharField()
    first_seen = models.DateTimeField()
    channel = models.IntegerField()
    rssi = models.IntegerField()
    signal_streng = models.CharField()
    current_latitude = models.DecimalField(max_digits=13, decimal_places=7)
    current_longitude = models.DecimalField(max_digits=13, decimal_places=7)
    altitude_meters = models.DecimalField(max_digits=10, decimal_places=2)
    accuracy_meters = models.DecimalField(max_digits=6, decimal_places=2)
    type = models.CharField()
    device_source = models.CharField()
    uploaded_by = models.TextField()
    # SQL Definition
    view_definition = WardrivingVendorsSQL.view_definition

    class Meta:
        managed = False
        db_table = "wardriving_vendor"
