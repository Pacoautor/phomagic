from django.contrib import admin
from .models import Category, Subcategory, ViewOption, GeneratedImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order", "slug", "image")
    list_editable = ("sort_order",)
    search_fields = ("name", "slug")
    ordering = ("sort_order", "name")


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "sort_order", "slug", "image")
    list_editable = ("sort_order",)
    list_filter = ("category",)
    search_fields = ("name", "slug", "category__name")
    ordering = ("category__sort_order", "category__name", "sort_order", "name")


@admin.register(ViewOption)
class ViewOptionAdmin(admin.ModelAdmin):
    list_display = ("name", "subcategory")
    list_filter = ("subcategory__category", "subcategory")
    search_fields = ("name", "subcategory__name", "subcategory__category__name")
    ordering = ("subcategory__category__sort_order", "subcategory__sort_order", "name")


@admin.register(GeneratedImage)
class GeneratedImageAdmin(admin.ModelAdmin):
    list_display = ("id", "subcategory", "viewoption", "created_at")
    list_filter = ("subcategory__category", "subcategory", "viewoption")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

