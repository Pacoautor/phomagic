
# products/urls.py
from django.urls import path
from . import views as pviews

urlpatterns = [
    path("", pviews.home, name="home"),

    # Lista de subcategorías de una categoría (por slug)
    path("c/<slug:category_slug>/", pviews.category_detail, name="category_detail"),

    # Lista de vistas disponibles para una subcategoría
    path("v/<int:subcategory_id>/", pviews.view_options, name="view_options"),

    # Formulario de generación (subcategory + view)
    path("g/<int:subcategory_id>/<int:view_id>/", pviews.generate_photo, name="generate_photo"),
]
