# photopro_app/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LoginView, LogoutView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("products.urls")),  # URLs de tu app principal
    path("login/", LoginView.as_view(template_name="registration/login.html"), name="login"),
    # Logout oficial; redirige al login tras cerrar sesión
    path("logout/", LogoutView.as_view(next_page="login"), name="logout"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
