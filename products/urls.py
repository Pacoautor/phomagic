# products/urls.py
from django.urls import path
from . import views as pviews

urlpatterns = [
    # Home (si tu home está en esta app; si no, borra esta línea)
    path("", pviews.home, name="home"),

    # Lista subcategorías de una categoría (por slug)
    path("c/<slug:category_slug>/", pviews.category_detail, name="category_detail"),

    # Lista de vistas (por id de subcategoría)
    path("v/<int:subcategory_id>/", pviews.view_options, name="view_options"),

    # Generar foto (por ids)
    path("g/<int:subcategory_id>/<int:view_id>/", pviews.generate_photo, name="generate_photo"),
]

