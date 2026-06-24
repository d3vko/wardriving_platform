import asyncio
import json
import re
import threading
from urllib.parse import urlencode

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APIRequestFactory, force_authenticate

from api.v1.wardrive.views import LteWardrivingViewSet, WifiWardrivingViewSet
from apps.wardriving.kml_export import (
    KmlExportError,
    LTE_KML_EXPORT,
    WIFI_KML_EXPORT,
    resolve_lte_kml_queryset,
    resolve_wifi_kml_queryset,
)
from apps.wardriving.kml_utils import KmlExportCancelled, build_kml_bytes

KML_HEARTBEAT_SECONDS = 60


def _render_drf_data(data):
    renderer = JSONRenderer()
    raw = renderer.render(data)
    return json.loads(raw.decode("utf-8"))


def _query_params_from_message(data: dict) -> dict[str, str]:
    skip = {"id"}
    out = {}
    for k, v in data.items():
        if k in skip or v is None:
            continue
        out[str(k)] = str(v)
    return out


def _filename_from_content_disposition(cd: str) -> str:
    if not cd:
        return "export.kml"
    m = re.search(r'filename="([^"]+)"', cd)
    if m:
        return m.group(1)
    m = re.search(r"filename=([^;\s]+)", cd)
    if m:
        return m.group(1).strip('"')
    return "export.kml"


def _run_wifi_kml(user, params: dict, cancel_event: threading.Event):
    try:
        queryset = resolve_wifi_kml_queryset(user, params)
    except KmlExportError as exc:
        return exc.status, {"detail": exc.detail}
    try:
        content = build_kml_bytes(
            queryset=queryset,
            pin_color=WIFI_KML_EXPORT["pin_color"],
            name_fn=WIFI_KML_EXPORT["name_fn"],
            lat_fn=WIFI_KML_EXPORT["lat_fn"],
            lon_fn=WIFI_KML_EXPORT["lon_fn"],
            should_cancel=cancel_event.is_set,
        )
    except KmlExportCancelled:
        return 499, {"detail": "KML export cancelled."}
    filename = WIFI_KML_EXPORT["filename_tpl"].format(username=user.username)
    return 200, (content, filename)


def _run_lte_kml(user, params: dict, cancel_event: threading.Event):
    try:
        queryset = resolve_lte_kml_queryset(user, params)
    except KmlExportError as exc:
        return exc.status, {"detail": exc.detail}
    try:
        content = build_kml_bytes(
            queryset=queryset,
            pin_color=LTE_KML_EXPORT["pin_color"],
            name_fn=LTE_KML_EXPORT["name_fn"],
            lat_fn=LTE_KML_EXPORT["lat_fn"],
            lon_fn=LTE_KML_EXPORT["lon_fn"],
            description_fn=LTE_KML_EXPORT["description_fn"],
            should_cancel=cancel_event.is_set,
        )
    except KmlExportCancelled:
        return 499, {"detail": "KML export cancelled."}
    filename = LTE_KML_EXPORT["filename_tpl"].format(username=user.username)
    return 200, (content, filename)


@sync_to_async(thread_sensitive=False)
def _wifi_kml(user, params: dict, cancel_event: threading.Event):
    return _run_wifi_kml(user, params, cancel_event)


@sync_to_async(thread_sensitive=False)
def _lte_kml(user, params: dict, cancel_event: threading.Event):
    return _run_lte_kml(user, params, cancel_event)


@sync_to_async
def _wifi_list(user, params: dict):
    factory = APIRequestFactory()
    qs = urlencode(params)
    path = f"/v1/wardrive/wifi/?{qs}" if qs else "/v1/wardrive/wifi/"
    request = factory.get(path)
    force_authenticate(request, user=user)
    view = WifiWardrivingViewSet.as_view({"get": "list"})
    response = view(request)
    return response.status_code, _render_drf_data(response.data)


@sync_to_async
def _lte_list(user, params: dict):
    factory = APIRequestFactory()
    qs = urlencode(params)
    path = f"/v1/wardrive/lte/?{qs}" if qs else "/v1/wardrive/lte/"
    request = factory.get(path)
    force_authenticate(request, user=user)
    view = LteWardrivingViewSet.as_view({"get": "list"})
    response = view(request)
    return response.status_code, _render_drf_data(response.data)


class _AuthWsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4001)
            return
        await self.accept()


class _KmlWsConsumer(_AuthWsConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cancel = threading.Event()

    async def disconnect(self, close_code):
        self._cancel.set()
        await super().disconnect(close_code)

    async def _await_kml(self, coro, msg_id: str):
        task = asyncio.create_task(coro)
        while not task.done():
            done, _ = await asyncio.wait({task}, timeout=KML_HEARTBEAT_SECONDS)
            if done:
                break
            if self._cancel.is_set():
                continue
            await self.send(
                text_data=json.dumps(
                    {"id": msg_id, "ok": True, "type": "kml_progress"},
                )
            )
        return await task


class WifiWardrivingListConsumer(_AuthWsConsumer):
    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(
                text_data=json.dumps(
                    {"id": None, "ok": False, "status": 400, "detail": "Invalid JSON."}
                )
            )
            return
        msg_id = data.get("id")
        params = _query_params_from_message(data)
        status, body = await _wifi_list(self.scope["user"], params)
        if status == 200:
            await self.send(
                text_data=json.dumps(
                    {"id": msg_id, "ok": True, "data": body}, default=str
                )
            )
        else:
            detail = body
            if isinstance(body, dict) and "detail" in body:
                detail = body["detail"]
            await self.send(
                text_data=json.dumps(
                    {
                        "id": msg_id,
                        "ok": False,
                        "status": status,
                        "detail": detail,
                    },
                    default=str,
                )
            )


class LteWardrivingListConsumer(_AuthWsConsumer):
    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(
                text_data=json.dumps(
                    {"id": None, "ok": False, "status": 400, "detail": "Invalid JSON."}
                )
            )
            return
        msg_id = data.get("id")
        params = _query_params_from_message(data)
        status, body = await _lte_list(self.scope["user"], params)
        if status == 200:
            await self.send(
                text_data=json.dumps(
                    {"id": msg_id, "ok": True, "data": body}, default=str
                )
            )
        else:
            detail = body
            if isinstance(body, dict) and "detail" in body:
                detail = body["detail"]
            await self.send(
                text_data=json.dumps(
                    {
                        "id": msg_id,
                        "ok": False,
                        "status": status,
                        "detail": detail,
                    },
                    default=str,
                )
            )


class WifiKmlConsumer(_KmlWsConsumer):
    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(
                text_data=json.dumps(
                    {"id": None, "ok": False, "status": 400, "detail": "Invalid JSON."}
                )
            )
            return
        msg_id = data.get("id")
        params = _query_params_from_message(data)
        await self.send(
            text_data=json.dumps(
                {"id": msg_id, "ok": True, "type": "kml_pending"},
            )
        )
        try:
            status, body = await self._await_kml(
                _wifi_kml(self.scope["user"], params, self._cancel),
                msg_id,
            )
        except Exception as exc:
            await self.send(
                text_data=json.dumps(
                    {
                        "id": msg_id,
                        "ok": False,
                        "status": 500,
                        "detail": f"KML generation failed: {exc}",
                    },
                    default=str,
                )
            )
            return
        if status == 499:
            return
        if status == 200:
            content, filename = body
            await self.send(
                text_data=json.dumps(
                    {
                        "id": msg_id,
                        "ok": True,
                        "type": "kml",
                        "filename": filename,
                    }
                )
            )
            await self.send(bytes_data=content)
        else:
            detail = body
            if isinstance(body, dict) and "detail" in body:
                detail = body["detail"]
            await self.send(
                text_data=json.dumps(
                    {
                        "id": msg_id,
                        "ok": False,
                        "status": status,
                        "detail": detail,
                    },
                    default=str,
                )
            )


class LteKmlConsumer(_KmlWsConsumer):
    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(
                text_data=json.dumps(
                    {"id": None, "ok": False, "status": 400, "detail": "Invalid JSON."}
                )
            )
            return
        msg_id = data.get("id")
        params = _query_params_from_message(data)
        await self.send(
            text_data=json.dumps(
                {"id": msg_id, "ok": True, "type": "kml_pending"},
            )
        )
        try:
            status, body = await self._await_kml(
                _lte_kml(self.scope["user"], params, self._cancel),
                msg_id,
            )
        except Exception as exc:
            await self.send(
                text_data=json.dumps(
                    {
                        "id": msg_id,
                        "ok": False,
                        "status": 500,
                        "detail": f"KML generation failed: {exc}",
                    },
                    default=str,
                )
            )
            return
        if status == 499:
            return
        if status == 200:
            content, filename = body
            await self.send(
                text_data=json.dumps(
                    {
                        "id": msg_id,
                        "ok": True,
                        "type": "kml",
                        "filename": filename,
                    }
                )
            )
            await self.send(bytes_data=content)
        else:
            detail = body
            if isinstance(body, dict) and "detail" in body:
                detail = body["detail"]
            await self.send(
                text_data=json.dumps(
                    {
                        "id": msg_id,
                        "ok": False,
                        "status": status,
                        "detail": detail,
                    },
                    default=str,
                )
            )
