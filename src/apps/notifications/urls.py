"""Rotas do app de notificações (montadas em ``/api/notifications/``)."""

from __future__ import annotations

from django.urls import path

from .views import PushSubscriptionDetailView, PushSubscriptionListCreateView

app_name = "notifications"

urlpatterns = [
    path(
        "subscriptions/",
        PushSubscriptionListCreateView.as_view(),
        name="subscription-list",
    ),
    path(
        "subscriptions/<int:pk>/",
        PushSubscriptionDetailView.as_view(),
        name="subscription-detail",
    ),
]
