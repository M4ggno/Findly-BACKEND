"""Rotas do app de auditoria (montadas em ``/api/``)."""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AuditEventViewSet, ItemHistoryView

app_name = "audit"

router = DefaultRouter()
router.register("audit", AuditEventViewSet, basename="audit-event")

urlpatterns = [
    # Rota aninhada do item; o router de itens não a captura porque o detalhe
    # usa um único segmento (``found/<public_code>/``).
    path(
        "items/found/<str:public_code>/history/",
        ItemHistoryView.as_view(),
        name="item-history",
    ),
    path("", include(router.urls)),
]
