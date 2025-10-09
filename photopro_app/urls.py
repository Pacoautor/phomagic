# photopro_app/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve as media_serve

urlpatterns = [
    path('admin/', admin.site.urls),

    # Home de la app
    path('', include('products.urls')),

    # ⚠️ Servir MEDIA también en producción (DEBUG=False)
    # Render no sirve MEDIA por ti; montamos /media/ desde MEDIA_ROOT.
    re_path(r'^media/(?P<path>.*)$', media_serve, {'document_root': settings.MEDIA_ROOT}),
]
