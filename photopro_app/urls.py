# photopro_app/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic.base import RedirectView
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage

# Redirección de favicon calculada EN CADA REQUEST (no al importar urls)
class FaviconRedirect(RedirectView):
    permanent = True

    def get_redirect_url(self, *args, **kwargs):
        try:
            # Usa el storage (manifest) en tiempo de petición
            return staticfiles_storage.url("favicon.ico")
        except Exception:
            # Fallback simple por si aún no existe en el manifest
            return settings.STATIC_URL + "favicon.ico"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("products.urls")),
    # si tienes login/logout aquí, déjalos como los tenías
    # path("login/", ... , name="login"),
    # path("logout/", ... , name="logout"),

    # Favicon seguro:
    re_path(r"^favicon\.ico$", FaviconRedirect.as_view()),
]
