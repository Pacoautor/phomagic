from django.contrib import admin
from .models import Category, Subcategory, ViewOption, GeneratedImage

# ===== Category =====
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "sort_order")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("sort_order",)
    ordering = ("sort_order", "name")


# ===== Subcategory =====
@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "name", "slug", "sort_order")
    list_filter = ("category",)
    search_fields = ("name", "slug", "category__name")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("sort_order",)
    ordering = ("category__sort_order", "sort_order", "name")


# ===== ViewOption (Vistas) =====
@admin.register(ViewOption)
class ViewOptionAdmin(admin.ModelAdmin):
    list_display = ("id", "subcategory", "name", "sort_order")
    list_filter = ("subcategory__category", "subcategory")
    search_fields = ("name", "subcategory__name", "subcategory__category__name")
    list_editable = ("sort_order",)
    ordering = ("subcategory__category__sort_order", "subcategory__sort_order", "sort_order", "name")


# ===== GeneratedImage =====
@admin.register(GeneratedImage)
class GeneratedImageAdmin(admin.ModelAdmin):
    """
    Admin sencillo para inspeccionar entradas/salidas generadas.
    El modelo GeneratedImage (products.models) **sí** tiene created_at (DateTimeField).
    """
    readonly_fields = ("created_at",)
    list_display = ("id", "category", "subcategory", "viewoption", "created_at")
    list_filter = ("category", "subcategory", "viewoption", "created_at")
    date_hierarchy = "created_at"
    search_fields = (
        "category__name",
        "subcategory__name",
        "viewoption__name",
    )
    ordering = ("-created_at",)
