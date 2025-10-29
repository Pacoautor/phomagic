from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),  # 👈 Ruta raíz dentro de products
    path('generate/', views.generate_image, name='generate_image'),
    path('processing/', views.processing, name='processing'),
    path('result/', views.result, name='result'),
]
