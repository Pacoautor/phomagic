from django.contrib import admin
from django.urls import path, include
from products import views as product_views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/", admin.site.urls),

    # Home
    path("", product_views.home, name="home"),

    # Login / Logout usando vistas de Django
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Registro personalizado
    path("signup/", product_views.signup, name="signup"),

    # Rutas de tu app
    path("products/", include("products.urls")),
]
