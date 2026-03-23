from rest_framework.routers import DefaultRouter

from .views import LtePlacesViewSet, WifiPlacesViewSet

router = DefaultRouter()

router.register(
    prefix="wifi-places",
    viewset=WifiPlacesViewSet,
    basename="wardrive-wifi-places",
)
router.register(
    prefix="lte-places",
    viewset=LtePlacesViewSet,
    basename="wardrive-lte-places",
)
