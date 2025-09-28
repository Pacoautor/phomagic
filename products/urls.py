# products/urls.py
from django.urls import path
from . import views as pviews

urlpatterns = [
    path("", pviews.home, name="home"),
    path("c/<slug:category_slug>/", pviews.subcategories, name="subcategories"),
    path("v/<int:subcategory_id>/", pviews.view_options, name="view_options"),
    path("g/<int:subcategory_id>/<int:view_id>/", pviews.generate_photo, name="generate_photo"),
    path("signup/", pviews.signup, name="signup"),  # <-- aquí el cambio
]
