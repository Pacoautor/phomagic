from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_photo, name='upload_photo'),
    path('select-category/', views.select_category, name='select_category'),
    path('select-view/', views.select_view, name='select_view'),
    path('processing/', views.processing, name='processing'),
]
