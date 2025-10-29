from django.contrib import admin
from django.urls import path, include
from products import views  # 👈 Importamos la vista index

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='home'),  # 👈 Esta línea crea la ruta "home"
    path('products/', include('products.urls')),  # 👈 Incluye las rutas de la app
]

# Para servir archivos estáticos y media en modo DEBUG
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
