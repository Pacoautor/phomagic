from django.contrib import admin
from .models import Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category')
    list_filter = ('category',)
    search_fields = ('name',)


@admin.register(ViewOption)
class ViewOptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'subcategory')
    list_filter = ('subcategory',)
    search_fields = ('name',)

from .models import Category, SubCategory, ViewOption, GeneratedImage

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "name")
    list_filter = ("category",)
    search_fields = ("name", "category__name")

@admin.register(ViewOption)
class ViewOptionAdmin(admin.ModelAdmin):
    list_display = ("id", "subcategory", "name")
    list_filter = ("subcategory__category", "subcategory")
    search_fields = ("name", "subcategory__name", "subcategory__category__name")

@admin.register(GeneratedImage)
class GeneratedImageAdmin(admin.ModelAdmin):
    list_display = ("id", "input_image", "output_image", "created_at")
    readonly_fields = ("created_at",)
