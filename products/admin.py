from django.contrib import admin
from .models import Category, SubCategory, ViewOption


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


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

