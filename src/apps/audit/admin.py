"""Admin da auditoria: somente leitura, sem criação/edição/exclusão."""

from __future__ import annotations

from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "item",
        "action",
        "previous_status",
        "new_status",
        "responsible",
        "created_at",
    )
    list_filter = ("action",)
    search_fields = (
        "item__public_code",
        "item__title",
        "responsible__full_name",
    )
    readonly_fields = (
        "item",
        "action",
        "previous_status",
        "new_status",
        "responsible",
        "metadata",
        "created_at",
    )
    list_select_related = ("item", "responsible")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
