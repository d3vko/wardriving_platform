from django.urls import re_path

from api.websockets.wardriving.consumers import (
    LteKmlConsumer,
    LteWardrivingListConsumer,
    WifiKmlConsumer,
    WifiWardrivingListConsumer,
)

websocket_urlpatterns = [
    re_path(r"^v1/wardrive/wifi/$", WifiWardrivingListConsumer.as_asgi()),
    re_path(r"^v1/wardrive/lte/$", LteWardrivingListConsumer.as_asgi()),
    re_path(r"^v1/wardrive/wifi/kml/$", WifiKmlConsumer.as_asgi()),
    re_path(r"^v1/wardrive/lte/kml/$", LteKmlConsumer.as_asgi()),
]
