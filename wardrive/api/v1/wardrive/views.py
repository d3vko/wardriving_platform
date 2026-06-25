import hashlib

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from django_filters import rest_framework as filters

from django.core.cache import cache
from django.db.models import Q

from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.misc.db_views import WardrivingVendorView
from apps.wardriving.filters import LteWardrivingFilterSet, WifiWardrivingFilterSet
from apps.wardriving.kml_export import (
    KmlExportError,
    LTE_KML_EXPORT,
    WIFI_KML_EXPORT,
    plan_wifi_kml_export,
    resolve_lte_kml_queryset,
    resolve_wifi_kml_queryset,
)
from apps.wardriving.kml_utils import build_kml_streaming_response, build_kml_zip_response
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
    "Exports KML optimized for Google My Maps (unzipped limit 5 MB per file). "
    "Each placemark includes full metadata in the popup description. "
    "**Required:** `first_seen_after` and `first_seen_before` (ISO 8601) to bound the range; "
    "same filters as the list endpoint (including full-day normalization). "
    "WiFi exports that exceed the size budget return a ZIP with multiple KML parts. "
    "LTE returns 413 if the estimated export exceeds the Maps size limit."
)


def _exclude_default_coords():
    return ~Q(current_latitude=0, current_longitude=0)


def _map_cache_key(prefix: str, user_pk, query_params) -> str:
    """Build a deterministic cache key scoped to a user and their query params."""
    sorted_qs = "&".join(
        f"{k}={v}"
        for k, v in sorted(query_params.items())
    )
    digest = hashlib.sha1(sorted_qs.encode()).hexdigest()[:16]
    return f"{prefix}:{user_pk}:{digest}"


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
        return WardrivingVendorView.objects.filter(
            uploaded_by=self.request.user.username
        ).order_by("-first_seen")

    @swagger_auto_schema(manual_parameters=list_params)
    def list(self, request, *args, **kwargs):
        key = _map_cache_key("wifi_list", request.user.pk, request.query_params)
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        cache.set(key, response.data)
        return response

    @swagger_auto_schema(
        manual_parameters=list_params,
        operation_description=kml_operation_description,
    )
    @action(methods=["get"], detail=False, url_path="kml")
    def download_kml(self, request, *args, **kwargs):
        try:
            queryset = resolve_wifi_kml_queryset(
                request.user,
                request.query_params,
            )
        except KmlExportError as exc:
            return Response({"detail": exc.detail}, status=exc.status)
        username = request.user.username
        mode, chunk_size = plan_wifi_kml_export(queryset.count())
        if mode == "single":
            return build_kml_streaming_response(
                queryset=queryset,
                filename=WIFI_KML_EXPORT["filename_tpl"].format(
                    username=username
                ),
                pin_color=WIFI_KML_EXPORT["pin_color"],
                name_fn=WIFI_KML_EXPORT["name_fn"],
                lat_fn=WIFI_KML_EXPORT["lat_fn"],
                lon_fn=WIFI_KML_EXPORT["lon_fn"],
                description_fn=WIFI_KML_EXPORT["description_fn"],
            )
        return build_kml_zip_response(
            queryset=queryset,
            chunk_size=chunk_size,
            zip_filename=WIFI_KML_EXPORT["zip_filename_tpl"].format(
                username=username
            ),
            part_filename_tpl=WIFI_KML_EXPORT["part_filename_tpl"],
            username=username,
            pin_color=WIFI_KML_EXPORT["pin_color"],
            name_fn=WIFI_KML_EXPORT["name_fn"],
            lat_fn=WIFI_KML_EXPORT["lat_fn"],
            lon_fn=WIFI_KML_EXPORT["lon_fn"],
            description_fn=WIFI_KML_EXPORT["description_fn"],
        )


class LteWardrivingViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """LTE points shaped like WiFi for the map UI."""

    serializer_class = LteWardrivingSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MapPlacesPagination
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = LteWardrivingFilterSet

    def get_queryset(self):
        return LTEWardriving.objects.filter(
            _exclude_default_coords(),
            uploaded_by=self.request.user.username,
        ).order_by("-first_seen")

    @swagger_auto_schema(manual_parameters=list_params)
    def list(self, request, *args, **kwargs):
        """Paginated list with optional filters."""
        key = _map_cache_key("lte_list", request.user.pk, request.query_params)
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        cache.set(key, response.data)
        return response

    @swagger_auto_schema(
        manual_parameters=list_params,
        operation_description=kml_operation_description,
    )
    @action(methods=["get"], detail=False, url_path="kml")
    def download_kml(self, request, *args, **kwargs):
        try:
            queryset = resolve_lte_kml_queryset(
                request.user,
                request.query_params,
            )
        except KmlExportError as exc:
            return Response({"detail": exc.detail}, status=exc.status)
        return build_kml_streaming_response(
            queryset=queryset,
            filename=LTE_KML_EXPORT["filename_tpl"].format(
                username=request.user.username
            ),
            pin_color=LTE_KML_EXPORT["pin_color"],
            name_fn=LTE_KML_EXPORT["name_fn"],
            lat_fn=LTE_KML_EXPORT["lat_fn"],
            lon_fn=LTE_KML_EXPORT["lon_fn"],
            description_fn=LTE_KML_EXPORT["description_fn"],
        )
