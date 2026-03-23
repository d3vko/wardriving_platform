from rest_framework import serializers

from apps.wardriving.db_views import WardrivingVendorsView
from apps.wardriving.models import LTEWardriving


def rssi_to_signal_strength(rssi: int) -> str:
    """Misma lógica que la vista SQL wardriving_vendor (LTE no usa la vista)."""
    if rssi > -50:
        return "Excellent"
    if -60 <= rssi <= -50:
        return "Good"
    if -70 <= rssi < -60:
        return "Fair"
    return "Weak"


class WifiWardrivingSerializer(serializers.ModelSerializer):
    """
    WiFi desde la vista SQL `wardriving_vendor`: vendor y signal_streng ya vienen
    del JOIN y del CASE en SQL (sin duplicar lógica en Python).
    """

    current_latitude = serializers.FloatField()
    current_longitude = serializers.FloatField()

    class Meta:
        model = WardrivingVendorsView
        fields = (
            "mac",
            "vendor",
            "ssid",
            "auth_mode",
            "device_source",
            "signal_streng",
            "uploaded_by",
            "type",
            "current_latitude",
            "current_longitude",
        )


class LteWardrivingSerializer(serializers.ModelSerializer):
    """Misma forma que WiFi para un solo tipo en el frontend."""

    mac = serializers.SerializerMethodField()
    vendor = serializers.CharField(source="provider")
    ssid = serializers.SerializerMethodField()
    auth_mode = serializers.SerializerMethodField()
    signal_streng = serializers.SerializerMethodField()
    type = serializers.CharField(source="tech")
    current_latitude = serializers.FloatField()
    current_longitude = serializers.FloatField()

    class Meta:
        model = LTEWardriving
        fields = (
            "mac",
            "vendor",
            "ssid",
            "auth_mode",
            "device_source",
            "signal_streng",
            "uploaded_by",
            "type",
            "current_latitude",
            "current_longitude",
        )

    def get_mac(self, obj: LTEWardriving) -> str:
        return f"{obj.mcc}-{obj.mnc}-{obj.lac}-{obj.cell_id}"

    def get_ssid(self, obj: LTEWardriving) -> str:
        return obj.band or ""

    def get_auth_mode(self, obj: LTEWardriving) -> str:
        return "LTE"

    def get_signal_streng(self, obj: LTEWardriving) -> str:
        return rssi_to_signal_strength(obj.rssi)
