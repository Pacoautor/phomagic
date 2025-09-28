from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from products import views as pviews

urlpatterns = [
    path("admin/", admin.site.urls),

    # Público
    path("", pviews.home, name="home"),
    path("c/<slug:category_slug>/", pviews.subcategories, name="subcategories"),
    path("v/<int:subcategory_id>/", pviews.view_options, name="view_options"),
    path("g/<int:subcategory_id>/<int:view_id>/", pviews.generate_photo, name="generate_photo"),

    # Auth
    path("accounts/", include("django.contrib.auth.urls")),  # login/logout/password reset
    path("accounts/", include("allauth.urls")),              # /accounts/… de allauth
    path("signup/", pviews.signup, name="signup"),           # tu vista de registro
]

# Media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
