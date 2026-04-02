from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from django_filters import rest_framework as filters

from django.db.models import Q

from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.misc.db_views import WardrivingVendorView
from apps.wardriving.filters import LteWardrivingFilterSet, WifiWardrivingFilterSet
from apps.wardriving.kml_utils import build_kml_response
from apps.wardriving.models import LTEWardriving

from api.pagination import MapPlacesPagination

from .serializers import LteWardrivingSerializer, WifiWardrivingSerializer

pagination_params = [
    openapi.Parameter(
        "page",
        openapi.IN_QUERY,
        description="Page number",
        type=openapi.TYPE_INTEGER,
    ),
    openapi.Parameter(
        "page_size",
        openapi.IN_QUERY,
        description="Page size (default 1000, max 2000 for map endpoints)",
        type=openapi.TYPE_INTEGER,
    ),
]

filter_params = [
    openapi.Parameter(
        "uploaded_by",
        openapi.IN_QUERY,
        description="Filter by substring in uploaded_by (case-insensitive contains)",
        type=openapi.TYPE_STRING,
    ),
    openapi.Parameter(
        "first_seen_after",
        openapi.IN_QUERY,
        description=(
            "first_seen lower bound (ISO 8601). Normalized to start of calendar day in the "
            "datetime's timezone (or TIME_ZONE if naive)."
        ),
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATETIME,
    ),
    openapi.Parameter(
        "first_seen_before",
        openapi.IN_QUERY,
        description=(
            "first_seen upper bound (ISO 8601). Normalized to end of calendar day in the "
            "datetime's timezone (or TIME_ZONE if naive)."
        ),
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATETIME,
    ),
]

list_params = pagination_params + filter_params

kml_operation_description = (
    "Exports KML for the authenticated user only. "
    "**Required:** `first_seen_after` and `first_seen_before` (ISO 8601) to bound the range "
    "and avoid timeouts; same filters as the list endpoint (including full-day normalization)."
)


def _exclude_default_coords():
    return ~Q(current_latitude=0, current_longitude=0)


class WifiWardrivingViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    WiFi points with real coordinates from the SQL view `wardriving_vendor`
    (vendor + signal strength computed in the database).
    """

    serializer_class = WifiWardrivingSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MapPlacesPagination
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = WifiWardrivingFilterSet

    def get_queryset(self):
        return WardrivingVendorView.objects.all()

    @swagger_auto_schema(manual_parameters=list_params)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        manual_parameters=list_params,
        operation_description=kml_operation_description,
    )
    @action(methods=["get"], detail=False, url_path="kml")
    def download_kml(self, request, *args, **kwargs):
        if not request.query_params.get(
            "first_seen_after"
        ) or not request.query_params.get("first_seen_before"):
            return Response(
                {
                    "detail": (
                        "KML export requires both first_seen_after and first_seen_before "
                        "(ISO 8601) with a bounded date range."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        queryset = self.filter_queryset(
            self.get_queryset().filter(uploaded_by=request.user.username)
        ).order_by("-first_seen")
        if not queryset.exists():
            return Response(
                {
                    "detail": "No WiFi samples to export for your user in this date range."
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return build_kml_response(
            queryset=queryset,
            filename=f"wifi_scans_{request.user.username}.kml",
            pin_color="ff00ffff",  # yellow
            name_fn=lambda o: o.ssid or o.mac,
            lat_fn=lambda o: o.current_latitude,
            lon_fn=lambda o: o.current_longitude,
            extra_fn=lambda o: {
                "vendor": o.vendor,
                "mac": o.mac,
                "ssid": o.ssid,
                "auth_mode": o.auth_mode,
                "signal_streng": o.signal_streng,
                "device_source": o.device_source,
                "uploaded_by": o.uploaded_by,
                "type": o.type,
                "first_seen": o.first_seen,
            },
        )


class LteWardrivingViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """LTE points shaped like WiFi for the map UI."""

    serializer_class = LteWardrivingSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MapPlacesPagination
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = LteWardrivingFilterSet

    def get_queryset(self):
        return LTEWardriving.objects.filter(_exclude_default_coords()).order_by(
            "-first_seen"
        )

    @swagger_auto_schema(manual_parameters=list_params)
    def list(self, request, *args, **kwargs):
        """Paginated list with optional filters."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        manual_parameters=list_params,
        operation_description=kml_operation_description,
    )
    @action(methods=["get"], detail=False, url_path="kml")
    def download_kml(self, request, *args, **kwargs):
        if not request.query_params.get(
            "first_seen_after"
        ) or not request.query_params.get("first_seen_before"):
            return Response(
                {
                    "detail": (
                        "KML export requires both first_seen_after and first_seen_before "
                        "(ISO 8601) with a bounded date range."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        queryset = self.filter_queryset(
            self.get_queryset().filter(uploaded_by=request.user.username)
        ).order_by("-first_seen")
        if not queryset.exists():
            return Response(
                {
                    "detail": "No LTE samples to export for your user in this date range."
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return build_kml_response(
            queryset=queryset,
            filename=f"lte_scans_{request.user.username}.kml",
            pin_color="ff0000ff",  # red
            name_fn=lambda o: f"{o.provider or 'LTE'} {o.cell_id}",
            lat_fn=lambda o: o.current_latitude,
            lon_fn=lambda o: o.current_longitude,
            extra_fn=lambda o: {
                "provider": o.provider,
                "cell_id": o.cell_id,
                "mcc": o.mcc,
                "mnc": o.mnc,
                "lac": o.lac,
                "band": o.band,
                "rssi": o.rssi,
                "tech": o.tech,
                "device_source": o.device_source,
                "uploaded_by": o.uploaded_by,
                "first_seen": o.first_seen,
            },
        )
