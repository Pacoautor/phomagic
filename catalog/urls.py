from django.urls import path
from .views import get_catalog, build_job, prepare_job, generate_job, upload_image

urlpatterns = [
    path("catalog/", get_catalog, name="get_catalog"),
    path("job/validate/", build_job, name="build_job"),
    path("job/prepare/", prepare_job, name="prepare_job"),
    path("job/generate/", generate_job, name="generate_job"),
    path("upload/", upload_image, name="upload_image"),  # <— NUEVO
]
