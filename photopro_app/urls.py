from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include

def healthz(_request):
    return HttpResponse("ok", content_type="text/plain")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", healthz, name="healthz"),   # para health checks en Render
    path("", include("products.urls")),         # tu app principal resuelve la portada "/"
]
