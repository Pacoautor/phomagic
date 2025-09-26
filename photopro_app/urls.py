# photopro_app/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("products.urls")),
    path("login/", include("django.contrib.auth.urls")),  # opcional si usas las vistas auth
]

# ⚠️ Servir MEDIA también en producción (Render)
# No lo limites a DEBUG; en Render lo necesitamos siempre.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
