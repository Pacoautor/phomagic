from django.urls import path
from . import views

urlpatterns = [
    # Página principal: subir imagen
    path('', views.upload_photo, name='home'),

    # Flujo de vistas
    path('upload/', views.upload_photo, name='upload_photo'),
    path('processing/', views.processing, name='processing'),

    # Opciones y selección
    path('view-options/', views.view_options, name='view_options'),
    path('select-category/', views.select_category_view, name='select_category_view'),

    # Resultados
    path('result/', views.result_view, name='result_view'),
]
