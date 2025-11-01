from django.urls import path
from . import views

urlpatterns = [
    path('', views.select_category, name='select_category'),
    path('select-category/', views.select_category, name='select_category'),
    path('select-view/', views.select_view, name='select_view'),
    path('set-view/', views.set_selected_view, name='set_selected_view'),
    path('upload/', views.upload_photo, name='upload_photo'),
    path('processing/', views.processing, name='processing'),
]
