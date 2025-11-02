from django.urls import path
from products import views

urlpatterns = [
    path("", views.select_category, name="select_category"),
    path("subcategory/<str:category>/", views.select_subcategory, name="select_subcategory"),
    path("view/<str:category>/<str:subcategory>/", views.select_view, name="select_view"),
    path("upload/", views.upload_photo, name="upload_photo"),
    path("processing/", views.processing, name="processing"),
]
