"""
Helpers para el envío de correos transaccionales de autenticación.

Todos los errores SMTP se capturan y loguean sin propagar,
para que un fallo de correo nunca bloquee el flujo del usuario.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


def _base_context(user):
    """Contexto compartido por todas las plantillas de correo."""
    return {
        "user": user,
        "user_name": user.get_full_name() or user.username,
        "site_name": getattr(settings, "EMAIL_SITE_NAME", "Wardrive"),
        "logo_url": getattr(settings, "EMAIL_LOGO_URL", ""),
        "support_email": getattr(settings, "EMAIL_SUPPORT_EMAIL", ""),
        "current_year": timezone.now().year,
    }


def send_password_reset_email(user, token: str, uid_b64: str) -> None:
    """Enviar correo de recuperación de contraseña con enlace al SPA."""
    base_url = getattr(settings, "PASSWORD_RESET_FRONTEND_BASE_URL", "").rstrip("/")
    path = getattr(settings, "PASSWORD_RESET_PATH", "reset-password").strip("/")
    reset_url = f"{base_url}/{path}?uid={uid_b64}&token={token}"

    context = {**_base_context(user), "reset_url": reset_url}
    html_body = render_to_string("emails/password_reset_email.html", context)
    text_body = f"Restablece tu contraseña en: {reset_url}"

    msg = EmailMultiAlternatives(
        subject=f"Restablece tu contraseña en {context['site_name']}",
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_body, "text/html")
    try:
        msg.send()
    except Exception:
        logger.exception("Error al enviar correo de reset a %s", user.email)


def send_welcome_email(user) -> None:
    """Enviar correo de bienvenida al registrarse un nuevo usuario."""
    login_url = getattr(settings, "FRONTEND_LOGIN_URL", "")
    welcome_intro = getattr(settings, "EMAIL_WELCOME_INTRO", "")
    features_raw = getattr(settings, "EMAIL_WELCOME_FEATURES", "")
    welcome_features = [line.strip() for line in features_raw.split("\n") if line.strip()]

    context = {
        **_base_context(user),
        "login_url": login_url,
        "app_url": login_url,
        "welcome_intro": welcome_intro,
        "welcome_features": welcome_features,
    }
    html_body = render_to_string("emails/welcome_email.html", context)

    features_text = "\n".join(f"- {f}" for f in welcome_features)
    text_body = (
        f"{welcome_intro}\n\n"
        f"¿Qué puedes hacer?\n{features_text}\n\n"
        f"Inicia sesión en: {login_url}"
    )

    msg = EmailMultiAlternatives(
        subject=f"Bienvenido a {context['site_name']}",
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_body, "text/html")
    try:
        msg.send()
    except Exception:
        logger.exception("Error al enviar correo de bienvenida a %s", user.email)
