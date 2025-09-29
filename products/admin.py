from django.contrib import admin
from .models import Category, Subcategory, ViewOption


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "has_image")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    # Importante: NO readonly, así puedes editar
    fields = ("name", "slug", "image")

    def has_image(self, obj):
        return bool(obj.image)
    has_image.boolean = True
    has_image.short_description = "Imagen"


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "slug", "has_image")
    list_filter = ("category",)
    search_fields = ("name", "category__name")
    prepopulated_fields = {"slug": ("name",)}
    fields = ("category", "name", "slug", "image")

    def has_image(self, obj):
        return bool(obj.image)
    has_image.boolean = True
    has_image.short_description = "Imagen"


@admin.register(ViewOption)
class ViewOptionAdmin(admin.ModelAdmin):
    list_display = ("name", "subcategory", "has_image")
    list_filter = ("subcategory__category", "subcategory")
    search_fields = ("name", "subcategory__name", "subcategory__category__name")
    fields = ("subcategory", "name", "image", "prompt_override")

    def has_image(self, obj):
        return bool(obj.image)
    has_image.boolean = True
    has_image.short_description = "Imagen"
