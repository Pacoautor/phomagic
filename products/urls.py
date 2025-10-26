from django.urls import path
from . import views

app_name = "products"

urlpatterns = [
    path("", views.select_category, name="select_category"),
    path("upload/", views.upload_photo, name="upload_photo"),
    path("processing/", views.processing, name="processing"),
    path("result/", views.result, name="result"),
    path("internal/lineas/upload/", views.upload_lineas_zip, name="upload_lineas_zip"),
]
