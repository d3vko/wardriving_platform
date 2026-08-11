"""
Verifica que ``_bulk_upsert_chunk`` encola la resolución de labels geográficos
post-commit (tarea Celery) en lugar de resolver síncrono dentro de la
transacción de write.

El cambio desacopla el cruce PostGIS (caro) del hot path de ``process_file``:
las columnas city/region/country quedan NULL hasta que la tarea async termine.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.files.utils import _bulk_upsert_chunk


class _FakeMeta:
    db_table = "wardriving"


class _FakeModel:
    _meta = _FakeMeta()
    objects = MagicMock()


class BulkUpsertGeosEnqueueTests(SimpleTestCase):
    @patch("apps.files.utils._load_existing_for_batch", return_value={})
    @patch("apps.wardriving.geos_labels.resolve_geos_labels_for_model_keys")
    @patch("apps.wardriving.geos_labels.enqueue_geos_labels_for_model_keys")
    @patch("apps.files.utils.transaction")
    def test_enqueues_post_commit_not_sync(
        self, txn, enqueue, sync_resolve, _load
    ):
        # Ejecuta el callback de on_commit de inmediato para poder assertar.
        captured = []

        def _capture_on_commit(cb):
            captured.append(cb)

        txn.on_commit = _capture_on_commit
        _FakeModel.objects.bulk_create.return_value = None
        _FakeModel.objects.bulk_update.return_value = 0

        row = {
            "uploaded_by": 1,
            "mac": "AA:BB:CC:DD:EE:01",
            "channel": 6,
            "rssi": -70,
        }
        created, updated, ignored, _ = _bulk_upsert_chunk(
            model=_FakeModel,
            key_fields=["uploaded_by", "mac", "channel"],
            best_by_key={(1, "AA:BB:CC:DD:EE:01", 6): row},
            better_obj_fn=lambda n, o: True,
            better_row_fn=lambda n, c: True,
            update_fields=["rssi"],
            only_fields=["id", "uploaded_by", "mac", "channel", "rssi"],
            base_filter=None,
            chunk_size=1000,
        )

        # La fila nueva fue escrita.
        self.assertEqual(created, 1)
        self.assertEqual(updated, 0)
        # Se registró un callback post-commit (no se resolvió síncrono).
        self.assertEqual(len(captured), 1)
        sync_resolve.assert_not_called()
        enqueue.assert_not_called()

        # Al disparar el callback (commit) se encola la tarea async.
        captured[0]()
        enqueue.assert_called_once()
        # Y sigue sin llamarse al resolve síncrono.
        sync_resolve.assert_not_called()

    @patch("apps.files.utils._load_existing_for_batch", return_value={})
    @patch("apps.wardriving.geos_labels.resolve_geos_labels_for_model_keys")
    @patch("apps.wardriving.geos_labels.enqueue_geos_labels_for_model_keys")
    @patch("apps.files.utils.transaction")
    def test_no_enqueue_when_nothing_written(self, txn, enqueue, sync_resolve, _load):
        txn.on_commit = lambda cb: cb()
        # best_by_key vacío -> nada que crear/actualizar -> no enqueue.
        created, updated, ignored, _ = _bulk_upsert_chunk(
            model=_FakeModel,
            key_fields=["uploaded_by", "mac", "channel"],
            best_by_key={},
            better_obj_fn=lambda n, o: True,
            better_row_fn=lambda n, c: True,
            update_fields=["rssi"],
            only_fields=["id", "uploaded_by", "mac", "channel", "rssi"],
            base_filter=None,
            chunk_size=1000,
        )
        self.assertEqual((created, updated), (0, 0))
        enqueue.assert_not_called()
        sync_resolve.assert_not_called()
