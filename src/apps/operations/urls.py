"""Rotas do app de operações (montadas em ``/api/operations/``)."""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ClaimViewSet,
    CollectionPointViewSet,
    CustodyTransferView,
    ItemClaimListCreateView,
    ItemCustodyView,
    ItemLabelView,
    WithdrawalConfirmView,
)

app_name = "operations"

router = DefaultRouter()
router.register("points", CollectionPointViewSet, basename="collection-point")
router.register("claims", ClaimViewSet, basename="claim")

urlpatterns = [
    path(
        "items/found/<str:public_code>/custody/",
        ItemCustodyView.as_view(),
        name="item-custody",
    ),
    path(
        "items/found/<str:public_code>/custody/transfer/",
        CustodyTransferView.as_view(),
        name="custody-transfer",
    ),
    path(
        "items/found/<str:public_code>/claims/",
        ItemClaimListCreateView.as_view(),
        name="item-claims",
    ),
    path(
        "items/found/<str:public_code>/label/",
        ItemLabelView.as_view(),
        name="item-label",
    ),
    path(
        "withdrawals/confirm/",
        WithdrawalConfirmView.as_view(),
        name="withdrawal-confirm",
    ),
    path("", include(router.urls)),
]
