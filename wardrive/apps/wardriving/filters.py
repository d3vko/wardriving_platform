from django_filters import rest_framework as filters

from apps.wardriving.db_views import WardrivingVendorsView
from apps.wardriving.models import LTEWardriving


class WifiPlacesFilter(filters.FilterSet):
    """Filtros opcionales para el listado mapa WiFi (vista SQL wardriving_vendor)."""

    uploaded_by = filters.CharFilter(field_name="uploaded_by", lookup_expr="icontains")
    first_seen_after = filters.DateTimeFilter(field_name="first_seen", lookup_expr="gte")
    first_seen_before = filters.DateTimeFilter(field_name="first_seen", lookup_expr="lte")

    class Meta:
        model = WardrivingVendorsView
        fields: list[str] = []


class LtePlacesFilter(filters.FilterSet):
    """Filtros opcionales para LTE (modelo LTEWardriving)."""

    uploaded_by = filters.CharFilter(field_name="uploaded_by", lookup_expr="icontains")
    first_seen_after = filters.DateTimeFilter(field_name="first_seen", lookup_expr="gte")
    first_seen_before = filters.DateTimeFilter(field_name="first_seen", lookup_expr="lte")

    class Meta:
        model = LTEWardriving
        fields: list[str] = []
