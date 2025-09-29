from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views as pviews

urlpatterns = [
    # Home (categorías) – requiere login
    path("", login_required(pviews.home), name="home"),

    # Detalle de categoría (subcategorías) – requiere login
    path("c/<slug:category_slug>/", login_required(pviews.category_detail), name="category_detail"),

    # Listado de vistas de una subcategoría – requiere login
    path("v/<int:subcategory_id>/", login_required(pviews.view_options), name="view_options"),

    # Generación – requiere login (por si alguien enlaza directo)
    path("g/<int:subcategory_id>/<int:view_id>/", login_required(pviews.generate_photo), name="generate_photo"),
]
