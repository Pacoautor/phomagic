from django.urls import path
from . import views

<<<<<<< HEAD
urlpatterns = [
    path('', views.index, name='index'),
    path('load_subcategories/', views.load_subcategories, name='load_subcategories'),
    path('load_views/', views.load_views, name='load_views'),
    path('upload/<int:view_id>/', views.upload_image, name='upload_image'),
=======
app_name = "products"

urlpatterns = [
    path("", views.select_category, name="select_category"),
    path("upload/", views.upload_photo, name="upload_photo"),
    path("processing/", views.processing, name="processing"),
    path("result/", views.result, name="result"),
    path("internal/lineas/upload/", views.upload_lineas_zip, name="upload_lineas_zip"),
>>>>>>> 54dc87cf5bddeb97076c30df6ac7fe69845bb4d6
]
