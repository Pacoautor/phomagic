# products/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("c/<str:category_name>/", views.subcategories, name="subcategories"),
    path("v/<int:subcategory_id>/", views.view_options, name="view_options"),  # NUEVO: elegir vista
    path("g/<int:subcategory_id>/<int:view_id>/", views.generate_photo, name="generate_photo"),  # generar con vista
]
