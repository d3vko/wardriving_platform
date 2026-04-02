import json
import re
from urllib.parse import urlencode

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APIRequestFactory, force_authenticate

from api.v1.wardrive.views import LteWardrivingViewSet, WifiWardrivingViewSet


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


@sync_to_async
def _wifi_kml(user, params: dict):
    factory = APIRequestFactory()
    qs = urlencode(params)
    path = f"/v1/wardrive/wifi/kml/?{qs}" if qs else "/v1/wardrive/wifi/kml/"
    request = factory.get(path)
    force_authenticate(request, user=user)
    view = WifiWardrivingViewSet.as_view({"get": "download_kml"})
    response = view(request)
    if response.status_code != 200:
        return response.status_code, _render_drf_data(response.data)
    filename = _filename_from_content_disposition(
        response.get("Content-Disposition", "")
    )
    return 200, (response.content, filename)


@sync_to_async
def _lte_kml(user, params: dict):
    factory = APIRequestFactory()
    qs = urlencode(params)
    path = f"/v1/wardrive/lte/kml/?{qs}" if qs else "/v1/wardrive/lte/kml/"
    request = factory.get(path)
    force_authenticate(request, user=user)
    view = LteWardrivingViewSet.as_view({"get": "download_kml"})
    response = view(request)
    if response.status_code != 200:
        return response.status_code, _render_drf_data(response.data)
    filename = _filename_from_content_disposition(
        response.get("Content-Disposition", "")
    )
    return 200, (response.content, filename)


class _AuthWsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4001)
            return
        await self.accept()


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


class WifiKmlConsumer(_AuthWsConsumer):
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
        status, body = await _wifi_kml(self.scope["user"], params)
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


class LteKmlConsumer(_AuthWsConsumer):
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
        status, body = await _lte_kml(self.scope["user"], params)
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
