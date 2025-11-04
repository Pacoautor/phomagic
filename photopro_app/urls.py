from django.urls import path
from products import views

urlpatterns = [
    path('upload/<str:category>/<str:subcategory>/<str:view_name>/', views.upload_photo, name='upload_photo'),
]
