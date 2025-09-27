# photopro_app/urls.py
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

from products import views as pviews  # usamos directamente las vistas

def logout_view(request):
    auth_logout(request)
    return redirect("login")

urlpatterns = [
    path("admin/", admin.site.urls),

    # Rutas públicas de la app (sin includes para evitar bucles)
    path("", pviews.home, name="home"),
    path("c/<slug:category_slug>/", pviews.subcategories, name="subcategories"),
    path("v/<int:subcategory_id>/", pviews.view_options, name="view_options"),
    path("g/<int:subcategory_id>/<int:view_id>/", pviews.generate_photo, name="generate_photo"),

    # Auth
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("signup/", pviews.signup, name="signup"),  # si tu vista existe; si no, bórrala
    path("logout/", logout_view, name="logout"),
]

# En Render (ahora con DEBUG=1) servimos media y estáticos solo si DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
