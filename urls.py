from django.contrib import admin
from django.urls import path, include
from products import views  # 👈 Importamos la vista index

urlpatterns = [
    path('admin/', admin.site.urls),

    # 👇 Ruta principal (home)
    path('', views.index, name='home'),

    # 👇 Rutas de la app products
    path('products/', include('products.urls')),
]

# 👇 Esto sirve para servir archivos de medios en modo DEBUG
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
