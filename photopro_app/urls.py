from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # Rutas existentes de tu app de producto
    path("", include("products.urls")),

    # Autenticación (django-allauth)
    path("accounts/", include("allauth.urls")),

    # NUEVO: API de catálogo
    path("api/", include("catalog.urls")),
]
