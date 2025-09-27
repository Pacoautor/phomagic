# photopro_app/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("products.urls")),

    # Favicon correcto (redirecciona a /static/... gestionado por WhiteNoise)
    path(
        "favicon.ico",
        RedirectView.as_view(url=staticfiles_storage.url("favicon.ico"), permanent=True),
        name="favicon"
    ),
]
