"""
Comprueba que API/Celery ven la misma BD y ayuda a contrastar conteos con el mapa.

Importante: los datos (y los pk de file_upload) son por entorno. Para validar un upload
concreto hay que ejecutar esto **en el servidor** donde corre el stack (mismo Postgres
que Celery), no en una copia local vacía.

Uso en el servidor (desde la raíz del proyecto, contenedor wardrive):
  podman-compose exec wardrive python wardrive/manage.py diagnose_celery_db
  podman-compose exec wardrive python wardrive/manage.py diagnose_celery_db --file-pk 410
  podman-compose exec wardrive python wardrive/manage.py diagnose_celery_db --uploaded-by usuario --first-seen-after 2026-04-01
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils.dateparse import parse_datetime


class Command(BaseCommand):
    help = (
        "Diagnóstico Celery vs BD en ESTE entorno. Ejecutar en el servidor donde procesó Celery; "
        "--file-pk es el id real de file_upload en esa base (no en local)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file-pk",
            type=int,
            default=None,
            help="PK de file_upload en esta BD (servidor); en local suele no existir el mismo id.",
        )
        parser.add_argument(
            "--uploaded-by",
            type=str,
            default=None,
            help="Filtro icontains sobre wardriving.uploaded_by (como el listado del mapa).",
        )
        parser.add_argument(
            "--first-seen-after",
            type=str,
            default=None,
            help="ISO 8601, ej. 2026-04-05T00:00:00-06:00",
        )
        parser.add_argument(
            "--first-seen-before",
            type=str,
            default=None,
            help="ISO 8601",
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE(
                "Diagnóstico sobre la BD conectada en ESTE proceso (ideal: servidor donde "
                "corre Celery). Los pk de file_upload no se comparten entre máquinas/entornos."
            )
        )
        db = settings.DATABASES["default"].copy()
        if db.get("PASSWORD"):
            db["PASSWORD"] = "***"
        self.stdout.write("DATABASES['default'] (password masked):")
        self.stdout.write(repr(db))
        self.stdout.write(f"DB vendor: {connection.vendor}")

        from apps.wardriving.models import Wardriving

        alive = Wardriving.objects.count()
        total_all = Wardriving.all_objects.count()
        self.stdout.write(
            f"wardriving: {alive} filas activas (manager por defecto), "
            f"{total_all} incl. soft-deleted (all_objects)."
        )

        try:
            from apps.misc.db_views import WardrivingVendorView

            vcount = WardrivingVendorView.objects.count()
            self.stdout.write(
                f"wardriving_vendor (vista del mapa WiFi): {vcount} filas visibles."
            )
        except Exception as exc:
            self.stdout.write(
                self.style.WARNING(f"No se pudo contar wardriving_vendor: {exc}")
            )

        file_pk = options["file_pk"]
        if file_pk is not None:
            from apps.files.models import FilesUploaded

            fu = FilesUploaded.objects.filter(pk=file_pk).first()
            if not fu:
                self.stdout.write(
                    self.style.ERROR(
                        f"file_upload pk={file_pk} no existe en esta base. "
                        f"Si es el id del log en otro entorno, ejecuta este comando en ese servidor "
                        f"(podman-compose exec wardrive …)."
                    )
                )
            else:
                self.stdout.write(
                    f"file_upload pk={fu.pk}: uploaded_by={fu.uploaded_by!r} "
                    f"device_source={fu.device_source!r} is_procesed={fu.is_procesed}"
                )
                exact = Wardriving.objects.filter(uploaded_by=fu.uploaded_by).count()
                self.stdout.write(
                    f"wardriving con uploaded_by exacto igual al del archivo: {exact}"
                )
                ic = Wardriving.objects.filter(
                    uploaded_by__icontains=fu.uploaded_by
                ).count()
                self.stdout.write(
                    f"wardriving con uploaded_by icontains (como API mapa): {ic}"
                )

        ub = options["uploaded_by"]
        if ub:
            qs = Wardriving.objects.filter(uploaded_by__icontains=ub)
            fa = options["first_seen_after"]
            fb = options["first_seen_before"]
            if fa:
                dt = parse_datetime(fa)
                if dt:
                    qs = qs.filter(first_seen__gte=dt)
                else:
                    self.stdout.write(self.style.WARNING(f"--first-seen-after no parseable: {fa!r}"))
            if fb:
                dt = parse_datetime(fb)
                if dt:
                    qs = qs.filter(first_seen__lte=dt)
                else:
                    self.stdout.write(self.style.WARNING(f"--first-seen-before no parseable: {fb!r}"))
            self.stdout.write(
                f"Filtro manual uploaded_by icontains {ub!r} "
                f"+ rango first_seen: {qs.count()} filas."
            )

        self.stdout.write("")
        self.stdout.write("Mapa (frontend): ruta típica /map con query params:")
        self.stdout.write("  first_seen_after, first_seen_before (ISO en URL)")
        self.stdout.write(
            "  Si hay sesión, se envía uploaded_by=<username> (icontains). "
            "Si el usuario del mapa no coincide con uploaded_by del upload, la lista puede ir vacía."
        )
        self.stdout.write(
            "Cliente SQL externo: debe usar el mismo host/puerto/base que este settings "
            "(desde el host suele ser localhost:puerto_publicado, no el hostname wardrive_db)."
        )
