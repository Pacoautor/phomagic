from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("products.urls")),
]

# Servir MEDIA también en producción (Render) — necesario para ver imágenes generadas
urlpatterns += [
    path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}, name="media"),
]
