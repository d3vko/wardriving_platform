import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .email import send_password_reset_email, send_welcome_email
from .serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserRegistrationSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()

_RESET_RESPONSE = openapi.Response(
    "Respuesta genérica (independiente de si el correo existe)",
    openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={"detail": openapi.Schema(type=openapi.TYPE_STRING)},
    ),
)


class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        # Correo de bienvenida: el fallo SMTP no bloquea el registro
        try:
            send_welcome_email(user)
        except Exception:
            logger.warning("No se pudo enviar welcome email a %s", user.email)

        return Response(
            {
                "user": serializer.data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "anon"

    @swagger_auto_schema(
        operation_summary="Solicitar restablecimiento de contraseña",
        operation_description=(
            "Envía un correo con el enlace de reset si el email está registrado. "
            "La respuesta es siempre idéntica para no filtrar si el correo existe."
        ),
        request_body=PasswordResetRequestSerializer,
        responses={200: _RESET_RESPONSE},
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        _GENERIC_RESPONSE = Response(
            {"detail": "Si el correo está registrado, recibirás instrucciones para restablecerla."},
            status=status.HTTP_200_OK,
        )

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            return _GENERIC_RESPONSE

        generator = PasswordResetTokenGenerator()
        token = generator.make_token(user)
        uid_b64 = urlsafe_base64_encode(force_bytes(user.pk))
        send_password_reset_email(user, token, uid_b64)

        return _GENERIC_RESPONSE


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Confirmar restablecimiento de contraseña",
        operation_description="Valida uid + token y establece la nueva contraseña.",
        request_body=PasswordResetConfirmSerializer,
        responses={
            200: openapi.Response(
                "Contraseña actualizada",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"detail": openapi.Schema(type=openapi.TYPE_STRING)},
                ),
            ),
            400: "Token inválido o contraseñas no coinciden",
        },
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        return Response(
            {"detail": "Contraseña actualizada correctamente."},
            status=status.HTTP_200_OK,
        )
