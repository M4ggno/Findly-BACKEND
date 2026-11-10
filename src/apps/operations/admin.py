"""Registro dos modelos de operações no Django Admin (caminho secreto)."""

from __future__ import annotations

from django.contrib import admin

from .models import Claim, CollectionPoint, CustodyRecord, WithdrawalAuthority


@admin.register(CollectionPoint)
class CollectionPointAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "capacity", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "address")
    filter_horizontal = ("operators",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(CustodyRecord)
class CustodyRecordAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "item",
        "held_by_user",
        "collection_point",
        "started_at",
        "ended_at",
    )
    list_filter = ("collection_point",)
    search_fields = ("item__public_code", "item__title", "note")
    list_select_related = ("item", "held_by_user", "collection_point")
    readonly_fields = (
        "item",
        "held_by_user",
        "collection_point",
        "note",
        "started_at",
        "ended_at",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ("id", "item", "claimant", "status", "reviewed_by", "created_at")
    list_filter = ("status",)
    search_fields = ("item__public_code", "item__title", "claimant__full_name")
    list_select_related = ("item", "claimant", "reviewed_by")
    readonly_fields = (
        "item",
        "claimant",
        "status",
        "message",
        "decision_note",
        "reviewed_by",
        "reviewed_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WithdrawalAuthority)
class WithdrawalAuthorityAdmin(admin.ModelAdmin):
    list_display = ("id", "claim", "expires_at", "used_at", "created_by", "created_at")
    list_filter = ("used_at",)
    search_fields = ("claim__item__public_code", "claim__claimant__full_name")
    list_select_related = ("claim__item", "created_by")
    readonly_fields = (
        "claim",
        "token",
        "qr_image",
        "expires_at",
        "used_at",
        "created_by",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
