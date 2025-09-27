
# photopro_app/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve as static_serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("products.urls")),
    path("accounts/", include("django.contrib.auth.urls")),  # login/logout nativos
]

# Servir MEDIA en producción también (para Render)
# OJO: esto sirve media con Django; suficiente para tu caso.
if settings.DEBUG:
    # En local, Django ya sirve STATIC. Añadimos MEDIA por comodidad.
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', static_serve, {'document_root': settings.MEDIA_ROOT}),
    ]
else:
    # En producción (Render), añade un handler para MEDIA también.
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', static_serve, {'document_root': settings.MEDIA_ROOT}),
    ]

# Importante: NO añadimos ninguna redirección al favicon con staticfiles_storage.
# El favicon lo serviremos como un estático normal desde la plantilla (luego lo vemos).
