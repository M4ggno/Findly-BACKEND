"""Registro das inscrições de push no Django Admin (caminho secreto)."""

from __future__ import annotations

from django.contrib import admin

from .models import PushSubscription


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "endpoint",
        "is_active",
        "last_used_at",
        "created_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("user__email", "endpoint", "user_agent")
    list_select_related = ("user",)
    readonly_fields = ("created_at", "updated_at", "last_used_at")
