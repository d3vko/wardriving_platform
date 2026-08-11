"""
Tests para el encolado asíncrono de labels geográficos.

El cruce PostGIS se movió fuera del hot path de ingest: ``enqueue_geos_labels_*``
colecta ids (SELECT barato) y encola la tarea Celery ``resolve_geos_labels`` en
vez de resolver síncrono dentro de la transacción de write. Estos tests cubren la
lógica de enqueue/fallback sin tocar PostGIS (no requieren DB espacial).
"""

from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.wardriving.geos_labels import (
    _validate_table,
    enqueue_geos_labels_for_model_keys,
)


class _FakeModel:
    """Modelo falso con solo lo que usa geos_labels (db_table)."""

    class _meta:
        db_table = "wardriving"


class _FakeLteModel:
    class _meta:
        db_table = "lte_wardriving"


class ValidateTableTests(SimpleTestCase):
    def test_rejects_unknown_table(self):
        with self.assertRaises(ValueError):
            _validate_table("not_a_table")

    def test_accepts_allowed_tables(self):
        self.assertEqual(_validate_table("wardriving"), "wardriving")
        self.assertEqual(_validate_table("lte_wardriving"), "lte_wardriving")


class EnqueueEmptyTests(SimpleTestCase):
    def test_empty_keys_returns_zero_without_task(self):
        # Sin keys -> collect_ids devuelve [] -> no se importa ni encola nada.
        with patch(
            "apps.wardriving.geos_labels.collect_ids_for_model_keys",
            return_value=[],
        ) as collect:
            with patch("apps.wardriving.tasks.resolve_geos_labels") as task:
                n = enqueue_geos_labels_for_model_keys(_FakeModel, ["mac"], [])
                self.assertEqual(n, 0)
                collect.assert_called_once()
                task.apply_async.assert_not_called()


class EnqueueApplyAsyncTests(SimpleTestCase):
    @patch("apps.wardriving.geos_labels.collect_ids_for_model_keys", return_value=[7, 8])
    @patch("apps.wardriving.tasks.resolve_geos_labels")
    def test_enqueues_task_with_table_and_ids(self, mock_task, _collect):
        n = enqueue_geos_labels_for_model_keys(_FakeLteModel, ["mcc"], [(1,)])
        mock_task.apply_async.assert_called_once_with(
            args=["lte_wardriving", [7, 8]]
        )
        self.assertEqual(n, 2)

    @patch("apps.wardriving.geos_labels.resolve_geos_labels_for_ids", return_value=5)
    @patch("apps.wardriving.geos_labels.collect_ids_for_model_keys", return_value=[1])
    @patch("apps.wardriving.tasks.resolve_geos_labels")
    def test_falls_back_to_sync_when_broker_fails(self, mock_task, _collect, sync_resolve):
        mock_task.apply_async.side_effect = RuntimeError("broker down")
        n = enqueue_geos_labels_for_model_keys(_FakeModel, ["mac"], [("a",)])
        # Fallback defensivo: resuelve síncrono para no perder labels.
        sync_resolve.assert_called_once_with("wardriving", [1])
        self.assertEqual(n, 5)
