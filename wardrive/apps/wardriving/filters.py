from django_filters import rest_framework as filters

from apps.core.utils import normalize_range_end, normalize_range_start
from apps.wardriving.db_views import WardrivingVendorsView
from apps.wardriving.models import LTEWardriving


class _FirstSeenDateRangeMixin:
    """
    ``first_seen_after`` / ``first_seen_before`` are normalized to the start and end of the
    calendar day in the value's timezone (or TIME_ZONE if naive).
    """

    first_seen_after = filters.DateTimeFilter(
        field_name="first_seen",
        method="filter_first_seen_after",
    )
    first_seen_before = filters.DateTimeFilter(
        field_name="first_seen",
        method="filter_first_seen_before",
    )

    def filter_first_seen_after(self, queryset, name, value):
        if value is None:
            return queryset
        return queryset.filter(**{f"{name}__gte": normalize_range_start(value)})

    def filter_first_seen_before(self, queryset, name, value):
        if value is None:
            return queryset
        return queryset.filter(**{f"{name}__lte": normalize_range_end(value)})


class WifiWardrivingFilterSet(_FirstSeenDateRangeMixin, filters.FilterSet):
    """Optional filters for the WiFi map list (SQL view ``wardriving_vendor``)."""

    uploaded_by = filters.CharFilter(field_name="uploaded_by", lookup_expr="icontains")

    class Meta:
        model = WardrivingVendorsView
        fields: list[str] = []


class LteWardrivingFilterSet(_FirstSeenDateRangeMixin, filters.FilterSet):
    """Optional filters for LTE (``LTEWardriving`` model)."""

    uploaded_by = filters.CharFilter(field_name="uploaded_by", lookup_expr="icontains")

    class Meta:
        model = LTEWardriving
        fields: list[str] = []
