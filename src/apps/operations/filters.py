"""Filtros de listagem do app de operações."""

from __future__ import annotations

from django.db.models import Count, F, Q
from django_filters import rest_framework as filters

from .models import Claim, ClaimStatus, CollectionPoint


class CollectionPointFilter(filters.FilterSet):
    """Filtros de ``GET /api/operations/points/``."""

    is_active = filters.BooleanFilter()
    has_capacity = filters.BooleanFilter(
        method="filter_has_capacity", label="Ainda tem capacidade"
    )
    operator = filters.NumberFilter(
        field_name="operators__id", label="Operador responsável"
    )

    class Meta:
        model = CollectionPoint
        fields = ["is_active", "operator", "has_capacity"]

    def filter_has_capacity(self, queryset, name, value):
        if not value:
            return queryset
        # Capacidade nula = ilimitada; os demais precisam ter vaga livre.
        return queryset.annotate(
            occupancy=Count(
                "custody_records", filter=Q(custody_records__ended_at__isnull=True)
            )
        ).filter(Q(capacity__isnull=True) | Q(occupancy__lt=F("capacity")))


class ClaimFilter(filters.FilterSet):
    """Filtros de ``GET /api/operations/claims/``."""

    status = filters.ChoiceFilter(choices=ClaimStatus.choices)
    item = filters.CharFilter(
        field_name="item__public_code", lookup_expr="iexact", label="Código do item"
    )
    claimant = filters.NumberFilter(field_name="claimant_id")
    mine = filters.BooleanFilter(method="filter_mine", label="Apenas meus claims")
    date_from = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    date_to = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Claim
        fields = ["status", "item", "claimant", "mine", "date_from", "date_to"]

    def filter_mine(self, queryset, name, value):
        if value:
            return queryset.filter(claimant=self.request.user)
        return queryset
