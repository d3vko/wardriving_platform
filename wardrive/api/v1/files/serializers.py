from rest_framework import serializers
from drf_yasg import openapi
from drf_yasg.utils import swagger_serializer_method

from apps.files.models import FilesUploaded
from apps.files.utils import safe_storage_name
from apps.wardriving import SourceDevice


class _SchemaOnlyUploadSerializer(serializers.Serializer):
    """Empty serializer used only for Swagger schema generation (avoids FileField inspection)."""

    pass


class FileUploadedListSerializer(serializers.ModelSerializer):
    class Meta:
        model = FilesUploaded
        fields = "__all__"
        read_only_fields = ["created_at"]


class MultipleFileUploadedCreateSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
    )
    device_source = serializers.ChoiceField(choices=SourceDevice.CHOICES)
    uploaded_by = serializers.CharField(required=False, allow_blank=True, default="")

    def create(self, validated_data):
        files = validated_data.pop("files")
        device_source = validated_data.get("device_source")
        uploaded_by = validated_data.get("uploaded_by", "")

        instances = []
        for f in files:
            f.name = safe_storage_name(getattr(f, "name", "upload"))
            instances.append(
                FilesUploaded.objects.create(
                    source=f, device_source=device_source, uploaded_by=uploaded_by
                )
            )
        return instances
