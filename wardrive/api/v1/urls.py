from django.urls import include, path

from .files.routers import router as files_router
from .files.views import DeviceSourceChoicesView

urlpatterns = [
    path("device-sources/", DeviceSourceChoicesView.as_view(), name="device-sources"),
    path("", include(files_router.urls)),
]
