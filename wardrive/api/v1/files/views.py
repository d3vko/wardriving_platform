from django.utils.translation import pgettext_lazy

from rest_framework import viewsets, permissions, status
from rest_framework.parsers import MultiPartParser
from rest_framework.decorators import parser_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from django_filters import rest_framework as filters

from .serializers import (
    FileUploadedListSerializer,
    MultipleFileUploadedCreateSerializer,
    _SchemaOnlyUploadSerializer,
)

from apps.files.models import FilesUploaded
from apps.wardriving import SourceDevice
from api.utils import is_swagger_fake_view
from api.pagination import CustomPagination

DEVICE_SOURCE_VALUES = [value for value, _ in SourceDevice.AVAILABLE_CHOICES]

upload_params = [
    openapi.Parameter(
        name="files",
        in_=openapi.IN_FORM,
        type=openapi.TYPE_FILE,
        description="Multiple files",
        required=True,
        collectionFormat="multi",
    ),
    openapi.Parameter(
        name="device_source",
        in_=openapi.IN_FORM,
        type=openapi.TYPE_STRING,
        required=True,
        description="Source device. Use GET /api/v1/device-sources/ for allowed values.",
        enum=DEVICE_SOURCE_VALUES,
    ),
]


@parser_classes([MultiPartParser])
class FilesUploadedViewSet(viewsets.ModelViewSet):
    lookup_field = "pk"
    queryset = FilesUploaded.objects.all()
    permission_classes = [
        permissions.IsAuthenticated,
    ]
    actions_serializers = {
        "list": FileUploadedListSerializer,
        "create": MultipleFileUploadedCreateSerializer,
    }
    pagination_class = CustomPagination
    filter_backends = [
        filters.DjangoFilterBackend,
    ]
    http_method_names = [
        "post",
    ]

    def get_serializer_class(self):
        if is_swagger_fake_view(self) and self.action == "create":
            return _SchemaOnlyUploadSerializer
        return self.actions_serializers.get(self.action, FileUploadedListSerializer)

    @swagger_auto_schema(
        manual_parameters=upload_params,
        responses={201: "Files uploaded successfully"},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instances = serializer.save()
        data = FileUploadedListSerializer(instances, many=True).data
        return Response(data, status=status.HTTP_201_CREATED)


class DeviceSourceChoicesView(APIView):
    """Return allowed device_source values for file uploads."""

    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_description="List allowed device_source values for the file upload endpoint.",
        responses={
            200: openapi.Response(
                description="List of choices",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "device_source": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "value": openapi.Schema(type=openapi.TYPE_STRING),
                                    "label": openapi.Schema(type=openapi.TYPE_STRING),
                                },
                            ),
                        ),
                    },
                ),
            )
        },
    )
    def get(self, request):
        choices = [
            {"value": value, "label": label} for value, label in SourceDevice.AVAILABLE_CHOICES
        ]
        return Response({"device_source": choices})
