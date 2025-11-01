from django.urls import path
from . import views

urlpatterns = [
    # Página principal: subir imagen
    path('', views.upload_photo, name='home'),

    # Subida de imagen y procesamiento
    path('upload/', views.upload_photo, name='upload_photo'),
    path('processing/', views.processing, name='processing'),

    # Resultado final
    path('result/', views.processing, name='result'),  # temporalmente usa la misma vista
]
