from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from django_filters import rest_framework as filters

from django.db.models import Q

from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.wardriving.db_views import WardrivingVendorsView
from apps.wardriving.filters import LteWardrivingFilterSet, WifiWardrivingFilterSet
from apps.wardriving.kml_utils import build_kml_response
from apps.wardriving.models import LTEWardriving

from api.pagination import MapPlacesPagination

from .serializers import LteWardrivingSerializer, WifiWardrivingSerializer

pagination_params = [
    openapi.Parameter(
        "page",
        openapi.IN_QUERY,
        description="Número de página",
        type=openapi.TYPE_INTEGER,
    ),
    openapi.Parameter(
        "page_size",
        openapi.IN_QUERY,
        description="Tamaño de página (por defecto 1000, máx. 2000 en mapas)",
        type=openapi.TYPE_INTEGER,
    ),
]

filter_params = [
    openapi.Parameter(
        "uploaded_by",
        openapi.IN_QUERY,
        description="Filtrar por texto en el campo uploaded_by (contiene, sin distinguir mayúsculas)",
        type=openapi.TYPE_STRING,
    ),
    openapi.Parameter(
        "first_seen_after",
        openapi.IN_QUERY,
        description="first_seen mayor o igual (ISO 8601)",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATETIME,
    ),
    openapi.Parameter(
        "first_seen_before",
        openapi.IN_QUERY,
        description="first_seen menor o igual (ISO 8601)",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATETIME,
    ),
]

list_params = pagination_params + filter_params


def _exclude_default_coords():
    return ~Q(current_latitude=0, current_longitude=0)


class WifiWardrivingViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Puntos WiFi con coordenadas reales desde la vista SQL `wardriving_vendor`
    (vendor + señal ya calculados en BD).
    """

    serializer_class = WifiWardrivingSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MapPlacesPagination
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = WifiWardrivingFilterSet

    def get_queryset(self):
        return WardrivingVendorsView.objects.all()

    @swagger_auto_schema(manual_parameters=list_params)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(methods=["get"], detail=False, url_path="kml")
    def download_kml(self, request, *args, **kwargs):
        queryset = (
            self.get_queryset()
            .filter(uploaded_by=request.user.username)
        )
        if not queryset.exists():
            return Response(
                {"detail": "No hay muestras WiFi para exportar en tu usuario."},
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
    """Puntos LTE homogeneizados al mismo shape que WiFi para el mapa."""

    serializer_class = LteWardrivingSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MapPlacesPagination
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = LteWardrivingFilterSet

    def get_queryset(self):
        return (
            LTEWardriving.objects.filter(_exclude_default_coords()).order_by("-first_seen")
        )

    @swagger_auto_schema(manual_parameters=list_params)
    def list(self, request, *args, **kwargs):
        """Listado paginado con filtros opcionales."""
        return super().list(request, *args, **kwargs)

    @action(methods=["get"], detail=False, url_path="kml")
    def download_kml(self, request, *args, **kwargs):
        queryset = (
            self.get_queryset()
            .filter(uploaded_by=request.user.username)
            .order_by("-first_seen")
        )
        if not queryset.exists():
            return Response(
                {"detail": "No hay muestras LTE para exportar en tu usuario."},
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
