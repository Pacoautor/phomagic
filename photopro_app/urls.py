# photopro_app/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from products import views as pviews # Necesitas importar esta vista

def logout_view(request):
    auth_logout(request)
    return redirect("login")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("products.urls")),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("signup/", pviews.signup_view, name="signup"), # Se añade la URL de registro
    path("logout/", logout_view, name="logout"),
]