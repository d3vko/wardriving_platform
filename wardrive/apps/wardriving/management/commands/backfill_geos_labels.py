"""
Backfill denormalized city/region/country/country_iso from geos_city.

Uso:
  python manage.py backfill_geos_labels --table all
  python manage.py backfill_geos_labels --table wardriving --batch-size 5000 --force
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.wardriving.geos_labels import (
    TABLE_LTE,
    TABLE_WARDRIVING,
    iter_id_batches,
    resolve_geos_labels_for_ids,
)


class Command(BaseCommand):
    help = (
        "Rellena city/region/country/country_iso en wardriving y/o lte_wardriving "
        "desde geos_city (set-based, reanudable)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            choices=("wardriving", "lte", "all"),
            default="all",
            help="Tabla(s) a procesar (default: all).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=5000,
            help="Ids por lote (default: 5000).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recomputar aunque country_iso ya esté relleno.",
        )
        parser.add_argument("--id-from", type=int, default=None)
        parser.add_argument("--id-to", type=int, default=None)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo cuenta ids pendientes; no escribe.",
        )
        parser.add_argument(
            "--verify-wifi-id",
            type=int,
            default=0,
            help="Tras backfill, imprime labels desde wardriving_vendor.",
        )
        parser.add_argument(
            "--verify-lte-id",
            type=int,
            default=0,
            help="Tras backfill, imprime labels desde wardriving_mobile.",
        )

    def handle(self, *args, **options):
        tables = []
        if options["table"] in ("wardriving", "all"):
            tables.append(TABLE_WARDRIVING)
        if options["table"] in ("lte", "all"):
            tables.append(TABLE_LTE)
        if not tables:
            raise CommandError("Sin tablas")

        batch_size = max(1, int(options["batch_size"]))
        force = bool(options["force"])
        dry_run = bool(options["dry_run"])

        for table in tables:
            self.stdout.write(self.style.NOTICE(f"=== {table} ==="))
            total_ids = 0
            total_updated = 0
            for batch in iter_id_batches(
                table,
                batch_size=batch_size,
                only_unresolved=not force,
                force=force,
                id_from=options["id_from"],
                id_to=options["id_to"],
            ):
                total_ids += len(batch)
                if dry_run:
                    self.stdout.write(
                        f"  [dry-run] batch ids={batch[0]}..{batch[-1]} n={len(batch)}"
                    )
                    continue
                updated = resolve_geos_labels_for_ids(table, batch, force=force)
                total_updated += updated
                self.stdout.write(
                    f"  batch ids={batch[0]}..{batch[-1]} "
                    f"n={len(batch)} updated={updated} cumulative={total_updated}"
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"{table}: ids_seen={total_ids} updated={total_updated} "
                    f"dry_run={dry_run} force={force}"
                )
            )

        self._verify(options)

    def _verify(self, options):
        wifi_id = int(options.get("verify_wifi_id") or 0)
        lte_id = int(options.get("verify_lte_id") or 0)
        checks = []
        if wifi_id:
            checks.append(("wardriving_vendor", wifi_id))
        if lte_id:
            checks.append(("wardriving_mobile", lte_id))
        if not checks:
            self.stdout.write(
                "Verificación sugerida:\n"
                "  SELECT city, region, country, country_iso FROM wardriving_vendor "
                "WHERE id = 779912;\n"
                "  EXPLAIN ANALYZE SELECT id FROM wardriving_vendor "
                "WHERE country_iso = 'US' LIMIT 50;\n"
                "  EXPLAIN ANALYZE SELECT id FROM wardriving_mobile "
                "WHERE country_iso = 'MX' LIMIT 50;"
            )
            return

        with connection.cursor() as cursor:
            for view, pk in checks:
                cursor.execute(
                    f"SELECT city, region, country, country_iso "
                    f"FROM {view} WHERE id = %s",
                    [pk],
                )
                row = cursor.fetchone()
                if row is None:
                    self.stdout.write(
                        self.style.WARNING(f"{view} id={pk}: no hay fila")
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{view} id={pk}: city={row[0]!r} "
                            f"region={row[1]!r} country={row[2]!r} "
                            f"country_iso={row[3]!r}"
                        )
                    )
