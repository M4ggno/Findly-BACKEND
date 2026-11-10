"""Rotas do app de itens (montadas em ``/api/items/``)."""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FoundItemViewSet, LostReportViewSet

app_name = "items"

router = DefaultRouter()
router.register("found", FoundItemViewSet, basename="found-item")
router.register("lost", LostReportViewSet, basename="lost-report")

urlpatterns = [
    path("", include(router.urls)),
]
