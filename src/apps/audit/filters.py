"""Filtros da listagem administrativa de auditoria."""

from __future__ import annotations

from django_filters import rest_framework as filters

from .models import AuditAction, AuditEvent


class AuditEventFilter(filters.FilterSet):
    """Filtros de ``GET /api/audit/``."""

    item = filters.CharFilter(
        field_name="item__public_code",
        lookup_expr="iexact",
        label="Código público do item",
    )
    action = filters.ChoiceFilter(choices=AuditAction.choices)
    date_from = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    date_to = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = AuditEvent
        fields = ["item", "action", "date_from", "date_to"]
