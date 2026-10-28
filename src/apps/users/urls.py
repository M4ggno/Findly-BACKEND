"""Rotas do app de usuários (montadas em ``/api/``)."""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MeView, UserViewSet

app_name = "users"

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    # Deve vir antes do router para não colidir com ``users/<pk>/``.
    path("users/me/", MeView.as_view(), name="me"),
    path("", include(router.urls)),
]
