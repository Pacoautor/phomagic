

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.generic.base import RedirectView
from django.templatetags.static import static

def logout_view(request):
    logout(request)
    return redirect("login")

urlpatterns = [
    path("admin/", admin.site.urls),
    # 👇 ESTA ES LA LÍNEA NUEVA
    path("favicon.ico", RedirectView.as_view(url=static("favicon.ico"), permanent=True)),
    path("", include("products.urls")),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", logout_view, name="logout"),
]