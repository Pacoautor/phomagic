from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('load_subcategories/', views.load_subcategories, name='load_subcategories'),
    path('load_views/', views.load_views, name='load_views'),
    path('upload_image/', views.upload_image, name='upload_image'),
]
