from rest_framework.routers import DefaultRouter

from .views import LteWardrivingViewSet, WifiWardrivingViewSet

router = DefaultRouter()

router.register(
    prefix="wifi",
    viewset=WifiWardrivingViewSet,
    basename="wardrive-wifi",
)
router.register(
    prefix="lte",
    viewset=LteWardrivingViewSet,
    basename="wardrive-lte",
)
