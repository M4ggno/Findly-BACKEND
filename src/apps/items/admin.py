"""Registro dos modelos de itens no Django Admin (caminho secreto)."""

from __future__ import annotations

from django.contrib import admin

from .models import FoundItem, ItemPhoto, LostReport


class ItemPhotoInline(admin.TabularInline):
    model = ItemPhoto
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(FoundItem)
class FoundItemAdmin(admin.ModelAdmin):
    list_display = (
        "public_code",
        "title",
        "category",
        "status",
        "reported_by",
        "found_at",
        "created_at",
    )
    list_filter = ("status", "category")
    search_fields = ("public_code", "title", "description", "found_location")
    readonly_fields = ("public_code", "created_at", "updated_at")
    date_hierarchy = "created_at"
    inlines = [ItemPhotoInline]


@admin.register(LostReport)
class LostReportAdmin(admin.ModelAdmin):
    list_display = (
        "public_code",
        "title",
        "category",
        "status",
        "owner",
        "lost_at",
        "created_at",
    )
    list_filter = ("status", "category")
    search_fields = ("public_code", "title", "description", "lost_location")
    readonly_fields = ("public_code", "created_at", "updated_at")
    date_hierarchy = "created_at"
