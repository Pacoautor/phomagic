from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('load_subcategories/', views.load_subcategories, name='load_subcategories'),
    path('load_views/', views.load_views, name='load_views'),
    path('upload/<int:view_id>/', views.upload_image, name='upload_image'),
]
