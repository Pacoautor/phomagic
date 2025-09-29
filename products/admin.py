# products/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Subcategory, ViewOption, GeneratedImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "sort_order", "image_thumb")
    list_editable = ("sort_order",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}

    def image_thumb(self, obj):
        if getattr(obj, "image_url", None):
            return format_html('<img src="{}" style="height:40px;max-width:80px;object-fit:cover;border-radius:4px;">', obj.image_url)
        return "—"
    image_thumb.short_description = "Imagen"


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ("category", "name", "slug", "sort_order", "image_thumb")
    list_editable = ("sort_order",)
    list_filter = ("category",)
    search_fields = ("name", "slug", "category__name")
    prepopulated_fields = {"slug": ("name",)}

    def image_thumb(self, obj):
        if getattr(obj, "image_url", None):
            return format_html('<img src="{}" style="height:40px;max-width:80px;object-fit:cover;border-radius:4px;">', obj.image_url)
        return "—"
    image_thumb.short_description = "Imagen"


@admin.register(ViewOption)
class ViewOptionAdmin(admin.ModelAdmin):
    list_display = ("subcategory", "name", "sort_order")
    list_editable = ("sort_order",)
    list_filter = ("subcategory__category", "subcategory")
    search_fields = ("name", "subcategory__name", "subcategory__category__name")


@admin.register(GeneratedImage)
class GeneratedImageAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "category", "subcategory", "viewoption", "input_image", "output_image")
    list_filter = ("category", "subcategory", "viewoption", "created_at")
    search_fields = ("id", "category__name", "subcategory__name", "viewoption__name")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)
