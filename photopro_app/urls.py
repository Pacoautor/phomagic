# photopro_app/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Todas las URLs de la app 'products' (incluye /, /c/... /v/... /g/... /signup/, etc.)
    path("", include("products.urls")),

    # Login/registro social de allauth (si lo usas)
    path("accounts/", include("allauth.urls")),
]

# Archivos estáticos y media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
