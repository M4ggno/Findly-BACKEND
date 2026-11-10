"""Filtros de listagem de achados e perdidos."""

from __future__ import annotations

from django_filters import rest_framework as filters

from .models import Category, FoundItem, ItemStatus, LostReport, LostReportStatus


class FoundItemFilter(filters.FilterSet):
    """Filtros de ``GET /api/items/found/``."""

    status = filters.ChoiceFilter(choices=ItemStatus.choices)
    category = filters.ChoiceFilter(choices=Category.choices)
    found_after = filters.IsoDateTimeFilter(field_name="found_at", lookup_expr="gte")
    found_before = filters.IsoDateTimeFilter(field_name="found_at", lookup_expr="lte")
    mine = filters.BooleanFilter(method="filter_mine", label="Apenas meus itens")

    class Meta:
        model = FoundItem
        fields = ["status", "category", "mine"]

    def filter_mine(self, queryset, name, value):
        if value:
            return queryset.filter(reported_by=self.request.user)
        return queryset


class LostReportFilter(filters.FilterSet):
    """Filtros de ``GET /api/items/lost/``."""

    status = filters.ChoiceFilter(choices=LostReportStatus.choices)
    category = filters.ChoiceFilter(choices=Category.choices)
    lost_after = filters.IsoDateTimeFilter(field_name="lost_at", lookup_expr="gte")
    lost_before = filters.IsoDateTimeFilter(field_name="lost_at", lookup_expr="lte")
    mine = filters.BooleanFilter(method="filter_mine", label="Apenas meus alertas")

    class Meta:
        model = LostReport
        fields = ["status", "category", "mine"]

    def filter_mine(self, queryset, name, value):
        if value:
            return queryset.filter(owner=self.request.user)
        return queryset
