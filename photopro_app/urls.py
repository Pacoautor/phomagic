# photopro_app/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin de Django
    path("admin/", admin.site.urls),

    # Todas las rutas de la app "products"
    path("", include("products.urls")),

    # Autenticación con django-allauth (login, logout, registro, etc.)
    path("accounts/", include("allauth.urls")),
]

# En modo DEBUG servimos los archivos media (imágenes subidas por usuarios)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
