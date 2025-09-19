from django.contrib import admin
from .models import Category, Subcategory, MasterPrompt

# Registra tus modelos aquí.
admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(MasterPrompt)
