from rest_framework.routers import DefaultRouter

from .views import UserRegistrationView

router = DefaultRouter()

router.register(
    prefix="auth-user",
    viewset=UserRegistrationView,
    basename="auth-user",
)
