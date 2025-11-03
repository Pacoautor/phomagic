from django.urls import path
from . import views

urlpatterns = [
    path('', views.select_category, name='select_category'),
    path('<str:category_name>/', views.select_subcategory, name='select_subcategory'),
    path('<str:category_name>/<str:subcategory_name>/', views.select_view, name='select_view'),
    path('upload/', views.upload_photo, name='upload_photo'),  # ← ESTA ES LA IMPORTANTE
]
