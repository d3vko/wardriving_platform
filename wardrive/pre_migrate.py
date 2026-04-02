"""
Pre-migrate script: fakea users.0001_initial en django_migrations si no existe.

Necesario al introducir AUTH_USER_MODEL = "users.User" en una BD existente donde
auth_user ya existe. Se ejecuta desde start.sh ANTES de manage.py migrate.
En deploys frescos o posteriores es un no-op.
"""

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wardrive.settings")
sys.path.insert(0, os.path.dirname(__file__))

import django

django.setup()

from django.db import connection, OperationalError


def fake_users_initial():
    try:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM django_migrations WHERE app=%s AND name=%s",
                ["users", "0001_initial"],
            )
            if cur.fetchone():
                print("[pre_migrate] users.0001_initial ya registrada, sin cambios.")
                return

            cur.execute(
                "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW())",
                ["users", "0001_initial"],
            )
            print("[pre_migrate] Fake de users.0001_initial insertado correctamente.")
    except OperationalError as exc:
        print(f"[pre_migrate] No se pudo conectar a la BD todavia, se omite: {exc}")


if __name__ == "__main__":
    fake_users_initial()
