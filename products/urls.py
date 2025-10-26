# products/urls.py
from django.urls import path
from . import views

app_name = "products"

urlpatterns = [
    path("", views.select_category, name="select_category"),
    path("upload/", views.upload_photo, name="upload_photo"),
    path("processing/", views.processing, name="processing"),
    path("result/", views.result, name="result"),
]
