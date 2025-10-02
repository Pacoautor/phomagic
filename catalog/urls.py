# catalog/urls.py
from django.urls import path
from .views import get_catalog, build_job


urlpatterns = [
    path("catalog/", get_catalog, name="get_catalog"),     # GET
    path("job/validate/", build_job, name="build_job"),    # POST
    path("job/prepare/", prepare_job, name="prepare_job"),  # <-- NUEVO
]
