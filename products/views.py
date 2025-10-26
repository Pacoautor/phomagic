# products/views.py
import os
import json
import uuid
import logging
from pathlib import Path

from django.conf import settings
from django.shortcuts import render, redirect
from django.core.files.storage import default_storage

from .forms import SelectCategoryForm  # <-- este sí existe en tu forms.py

# Formulario mínimo de subida definido aquí para no tocar products/forms.py
from django import forms
class UploadForm(forms.Form):
    image = forms.ImageField(label="Selecciona una imagen")


logger = logging.getLogger("django")


# ----------------------------------------------------------
# Utilidad: asegurar estructura de directorios en /data/media
# ----------------------------------------------------------
def ensure_dirs():
    base = Path(settings.MEDIA_ROOT)
    for sub in ("uploads/input", "uploads/output", "uploads/tmp"):
        (base / sub).mkdir(parents=True, exist_ok=True)


# ----------------------------------------------------------
# Paso 1: selección inicial
# ----------------------------------------------------------
def select_category(request):
    ensure_dirs()

    if request.method == "POST":
        # Logs de diagnóstico
        logger.info("=== SELECT_CATEGORY POST ===")
        logger.info(f"Session ID: {request.session.session_key}")
        logger.info(f"POST DATA: {request.POST}")

        form = SelectCategoryForm(request.POST)
        if form.is_valid():
            selection = form.cleaned_data
            request.session["selection"] = selection
            request.session.modified = True
            logger.info(f"Selection stored in session: {selection}")
            return redirect("upload_photo")
    else:
        form = SelectCategoryForm()

    return render(request, "products/select_category.html", {"form": form})


# ----------------------------------------------------------
# Paso 2: subir imagen
# ----------------------------------------------------------
def upload_photo(request):
    ensure_dirs()
    selection = request.session.get("selection")
    if not selection:
        logger.warning("Upload attempted without selection in session.")
        return redirect("select_category")

    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.cleaned_data["image"]
            # Guarda en uploads/input
            rel_path = default_storage.save(os.path.join("uploads/input", image.name), image)
            input_path = os.path.join(settings.MEDIA_ROOT, rel_path)

            # Persistimos job
            job_id = str(uuid.uuid4())
            tmp_file = os.path.join(settings.MEDIA_ROOT, "uploads/tmp", f"{job_id}.json")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump({"selection": selection, "input_path": input_path, "output_path": ""}, f)

            request.session["job_id"] = job_id
            request.session.modified = True
            return redirect("processing")
    else:
        form = UploadForm()

    return render(request, "products/upload_photo.html", {"form": form, "selection": selection})


# ----------------------------------------------------------
# Paso 3: procesamiento (stub seguro)
# ----------------------------------------------------------
def processing(request):
    ensure_dirs()
    job_id = request.session.get("job_id")
    if not job_id:
        return redirect("select_category")

    tmp_file = os.path.join(settings.MEDIA_ROOT, "uploads/tmp", f"{job_id}.json")
    if not os.path.exists(tmp_file):
        return redirect("select_category")

    with open(tmp_file, "r", encoding="utf-8") as f:
        job = json.load(f)

    # Aquí iría tu lógica real (OpenAI, PIL, etc.). Para probar el flujo, generamos un “output” dummy.
    output_path = os.path.join(settings.MEDIA_ROOT, "uploads/output", f"{job_id}.png")
    # Creamos un archivo placeholder si no existe
    if not os.path.exists(output_path):
        with open(output_path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")  # cabecera PNG vacía para no romper la vista

    job["output_path"] = output_path
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(job, f)

    request.session["job_id"] = job_id
    request.session.modified = True
    return redirect("result")


# ----------------------------------------------------------
# Paso 4: resultado
# ----------------------------------------------------------
def result(request):
    ensure_dirs()
    job_id = request.session.get("job_id")
    if not job_id:
        return redirect("select_category")

    tmp_file = os.path.join(settings.MEDIA_ROOT, "uploads/tmp", f"{job_id}.json")
    if not os.path.exists(tmp_file):
        return redirect("select_category")

    with open(tmp_file, "r", encoding="utf-8") as f:
        job = json.load(f)

    return render(
        request,
        "products/result.html",
        {
            "output_path": job.get("output_path"),
            "selection": job.get("selection", {}),
        },
    )
