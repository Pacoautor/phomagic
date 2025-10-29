from django.urls import path
from . import views

urlpatterns = [
    # Ruta principal - selección de categoría
    path('', views.select_category, name='home'),
    
    # AJAX endpoints para cargar opciones dinámicamente
    path('load_subcategories/', views.load_subcategories, name='load_subcategories'),
    path('load_views/', views.load_views, name='load_views'),
    
    # Flujo principal de la aplicación
    path('upload/', views.upload_photo, name='upload_photo'),
    path('processing/', views.processing, name='processing'),
    path('result/', views.result, name='result'),
    
    # Subida de líneas (protegida)
    path('upload-lineas/', views.upload_lineas_zip, name='upload_lineas_zip'),
]