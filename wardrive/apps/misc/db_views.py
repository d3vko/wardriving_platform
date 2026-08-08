from django.db import models
from django_db_views.db_view import DBView

from apps.misc.sql_views import (
    WardrivingMobileSQL,
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
    city = models.CharField()
    region = models.CharField()
    country = models.CharField()
    country_iso = models.CharField()
    # SQL Definition
    view_definition = WardrivingVendorsSQL.view_definition

    class Meta:
        managed = False
        db_table = "wardriving_vendor"


class WardrivingMobileView(DBView):
    id = models.BigIntegerField(primary_key=True)
    mcc = models.IntegerField()
    mnc = models.IntegerField()
    lac = models.IntegerField()
    cell_id = models.IntegerField()
    cell_type = models.CharField()
    state = models.SmallIntegerField()
    enodeb_id = models.BigIntegerField()
    sector_id = models.SmallIntegerField()
    pci = models.SmallIntegerField()
    band = models.TextField()
    earfcn = models.IntegerField()
    dl_freq_mhz = models.DecimalField(max_digits=8, decimal_places=1)
    ul_freq_mhz = models.DecimalField(max_digits=8, decimal_places=1)
    rssi = models.IntegerField()
    rsrp = models.IntegerField()
    rsrq = models.IntegerField()
    sinr = models.IntegerField()
    signal_streng = models.CharField()
    provider = models.TextField()
    tech = models.TextField()
    first_seen = models.DateTimeField()
    device_source = models.CharField()
    uploaded_by = models.TextField()
    current_latitude = models.DecimalField(max_digits=13, decimal_places=7)
    current_longitude = models.DecimalField(max_digits=13, decimal_places=7)
    city = models.CharField()
    region = models.CharField()
    country = models.CharField()
    country_iso = models.CharField()
    # SQL Definition
    view_definition = WardrivingMobileSQL.view_definition

    class Meta:
        managed = False
        db_table = "wardriving_mobile"
