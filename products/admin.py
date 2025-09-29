from django.contrib import admin
from .models import Category, Subcategory, ViewOption, GeneratedImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category")
    list_filter = ("category",)
    search_fields = ("name", "category__name")


@admin.register(ViewOption)
class ViewOptionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "subcategory", "strength")
    list_filter = ("subcategory__category", "subcategory")
    search_fields = ("name", "subcategory__name", "subcategory__category__name")


@admin.register(GeneratedImage)
class GeneratedImageAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "category", "subcategory", "view_option", "created_at")
    list_filter = ("category", "subcategory", "view_option", "created_at")
    search_fields = ("user__username", "category__name", "subcategory__name", "view_option__name")
    readonly_fields = ("created_at",)
