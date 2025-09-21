# photopro_app/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# importamos la vista de registro que definiste en products.views
from products.views import signup_view

from django.contrib.auth import views as auth_views
from django.contrib.auth import logout
from django.shortcuts import redirect


def logout_view(request):
    logout(request)
    return redirect("login")


urlpatterns = [
    path("admin/", admin.site.urls),

    # autenticación
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", logout_view, name="logout"),
    path("signup/", signup_view, name="signup"),   # <- ESTA ES LA QUE FALTABA

    # app principal
    path("", include("products.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
