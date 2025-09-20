# products/admin.py
from django.contrib import admin
from .models import Category, Subcategory, ViewOption, MasterPrompt

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category")
    list_filter = ("category",)
    search_fields = ("name",)

@admin.register(ViewOption)
class ViewOptionAdmin(admin.ModelAdmin):
    list_display = ("name", "subcategory")
    list_filter = ("subcategory__category", "subcategory")
    search_fields = ("name",)

@admin.register(MasterPrompt)
class MasterPromptAdmin(admin.ModelAdmin):
    list_display = ("subcategory", "view")
    list_filter = ("subcategory__category", "subcategory", "view")
    search_fields = ("prompt_text",)

