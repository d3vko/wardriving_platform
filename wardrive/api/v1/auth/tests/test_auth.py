"""
Tests de autenticación REST: login dual (username/email), reset de contraseña,
registro con welcome email.

Ejecutar dentro del contenedor:
    podman-compose exec wardrive python wardrive/manage.py test api.v1.auth.tests
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import mail
from django.test import TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()

EMAIL_SETTINGS = {
    "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
    "EMAIL_SITE_NAME": "TestApp",
    "EMAIL_LOGO_URL": "",
    "EMAIL_SUPPORT_EMAIL": "",
    "PASSWORD_RESET_FRONTEND_BASE_URL": "http://localhost:5173/ctf",
    "PASSWORD_RESET_PATH": "reset-password",
    "FRONTEND_LOGIN_URL": "http://localhost:5173/ctf/login",
    "EMAIL_WELCOME_INTRO": "Bienvenido al CTF de prueba.\nTu cuenta está lista.",
    "EMAIL_WELCOME_FEATURES": "Subir capturas\nVer mapas\nAnalytics",
}


@override_settings(**EMAIL_SETTINGS)
class LoginDualTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="SecurePass123!",
        )
        self.url = "/v1/auth/login/"

    def test_login_with_username(self):
        res = self.client.post(
            self.url, {"username": "testuser", "password": "SecurePass123!"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        self.assertEqual(res.data["username"], "testuser")

    def test_login_with_email(self):
        res = self.client.post(
            self.url, {"username": "test@example.com", "password": "SecurePass123!"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertEqual(res.data["username"], "testuser")

    def test_login_email_case_insensitive(self):
        res = self.client.post(
            self.url, {"username": "TEST@EXAMPLE.COM", "password": "SecurePass123!"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_login_wrong_password(self):
        res = self.client.post(
            self.url, {"username": "testuser", "password": "wrongpassword"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self):
        res = self.client.post(
            self.url, {"username": "nobody", "password": "SecurePass123!"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(**EMAIL_SETTINGS)
class PasswordResetRequestTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="resetuser",
            email="reset@example.com",
            password="OldPass123!",
        )
        self.url = "/v1/auth/password/reset/"

    def test_reset_existing_email_returns_generic(self):
        res = self.client.post(self.url, {"email": "reset@example.com"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("detail", res.data)

    def test_reset_nonexistent_email_returns_same_generic(self):
        res = self.client.post(self.url, {"email": "nobody@example.com"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("detail", res.data)

    def test_reset_existing_email_sends_mail(self):
        self.client.post(self.url, {"email": "reset@example.com"}, format="json")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset@example.com", mail.outbox[0].to)

    def test_reset_nonexistent_email_sends_no_mail(self):
        self.client.post(self.url, {"email": "ghost@example.com"}, format="json")
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_invalid_email_format(self):
        res = self.client.post(self.url, {"email": "notanemail"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(**EMAIL_SETTINGS)
class PasswordResetConfirmTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="confirmuser",
            email="confirm@example.com",
            password="OldPass123!",
        )
        self.url = "/v1/auth/password/reset/confirm/"
        generator = PasswordResetTokenGenerator()
        self.token = generator.make_token(self.user)
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))

    def test_confirm_valid_token_changes_password(self):
        res = self.client.post(
            self.url,
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": "NewSecurePass456!",
                "new_password_confirm": "NewSecurePass456!",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewSecurePass456!"))

    def test_confirm_invalid_token(self):
        res = self.client.post(
            self.url,
            {
                "uid": self.uid,
                "token": "invalid-token",
                "new_password": "NewSecurePass456!",
                "new_password_confirm": "NewSecurePass456!",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_invalid_uid(self):
        res = self.client.post(
            self.url,
            {
                "uid": "invalid-uid",
                "token": self.token,
                "new_password": "NewSecurePass456!",
                "new_password_confirm": "NewSecurePass456!",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_passwords_do_not_match(self):
        res = self.client.post(
            self.url,
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": "NewSecurePass456!",
                "new_password_confirm": "DifferentPass789!",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_token_cannot_be_reused(self):
        """Tras cambiar la contraseña, el mismo token debe quedar inválido."""
        payload = {
            "uid": self.uid,
            "token": self.token,
            "new_password": "NewSecurePass456!",
            "new_password_confirm": "NewSecurePass456!",
        }
        self.client.post(self.url, payload, format="json")
        res2 = self.client.post(self.url, payload, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(**EMAIL_SETTINGS)
class RegistrationWelcomeEmailTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/v1/auth/register/"

    def test_register_sends_welcome_email(self):
        res = self.client.post(
            self.url,
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertIn("newuser@example.com", msg.to)

        # El cuerpo plano incluye el intro y la primera feature
        self.assertIn("Bienvenido al CTF de prueba", msg.body)
        self.assertIn("- Subir capturas", msg.body)
        self.assertIn("http://localhost:5173/ctf/login", msg.body)

        # El cuerpo HTML incluye el intro y al menos un <li> de features
        html_bodies = [b for b, mime in msg.alternatives if mime == "text/html"]
        self.assertEqual(len(html_bodies), 1)
        html = html_bodies[0]
        self.assertIn("Bienvenido al CTF de prueba", html)
        self.assertIn("<li", html)
        self.assertIn("Subir capturas", html)
