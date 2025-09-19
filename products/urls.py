from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("c/<str:category_name>/", views.subcategories, name="subcategories"),
    path("g/<int:subcategory_id>/", views.generate_photo, name="generate_photo"),
    # Si tienes una vista de prueba para OpenAI, puedes añadirla:
    # path("test-openai/", views.test_openai, name="test_openai"),
]
