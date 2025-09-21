# products/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.category_list, name="category_list"),
    path("c/<slug:category_slug>/", views.subcategories, name="subcategories"),

    # ⬇️ NUEVA: selector de vista para una subcategoría
    path("v/<int:subcategory_id>/", views.view_options, name="view_options"),

    # (esto ya lo tenías) generar imagen
    path(
        "generate/<int:subcategory_id>/<int:view_id>/",
        views.generate_photo,
        name="generate_photo",
    ),
]