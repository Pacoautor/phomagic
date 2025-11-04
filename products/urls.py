from django.urls import path
from . import views

urlpatterns = [
    path('', views.select_category, name='select_category'),
    path('subcategory/<str:category>/', views.select_subcategory, name='select_subcategory'),
    path('view/<str:category>/<str:subcategory>/', views.view_products, name='view_products'),
    path('upload/<str:category>/<str:subcategory>/<str:view_name>/', views.upload_photo, name='upload_photo'),
]
