from django.contrib import admin
from django.urls import path, include
from products import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),  # ← esta es la página raíz
    path('products/', include('products.urls')),
]
