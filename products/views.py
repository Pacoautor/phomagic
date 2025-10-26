import os
import json
import uuid
import logging
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import JsonResponse
from .forms import SelectionForm, UploadForm
from openai import OpenAI
from PIL import Image
import numpy as np
from docx import Document

logger = logging.getLogger("django")
client = OpenAI(api_key=settings.OPENAI_API_KEY)


# ----------------------------------------------------------
# Función auxiliar para crear directorios si no existen
# ----------------------------------------------------------
def ensure_dirs():
    os.makedirs(os.path.join(settings.MEDIA_ROOT, "uploads", "input"), exist_ok=True)
    os.makedirs(os.path.join(settings.MEDIA_ROOT, "uploads", "output"), exist_ok=True)
    os.makedirs(os.path.join(settings.MEDIA_ROOT, "uploads", "tmp"), exist_ok=True)


# ----------------------------------------------------------
# Página principal: selección de categoría
# ----------------------------------------------------------
def select_category(request):
    ensure_dirs()

    if request.method == "POST":
        # ==== LÍNEAS DE DEPURACIÓN AÑADIDAS ====
        logger.info("=== SELECT_CATEGORY POST ===")
        logger.info(f"Session ID: {request.session.session_key}")
        logger.info(f"POST DATA: {request.POST}")
        # ========================================

        form = SelectionForm(request.POST)
        if form.is_valid():
            selection = form.cleaned_data
            request.session["selection"] = selection
            request.session.modified = True
            logger.info(f"Selection stored in session: {selection}")
            return redirect("upload_photo")
    else:
        form = SelectionForm()

    return render(request, "products/select_category.html", {"form": form})


# ----------------------------------------------------------
# Subida de imagen
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
            filename = default_storage.save(
                os.path.join("uploads/input", image.name), image
            )
            input_path = os.path.join(settings.MEDIA_ROOT, filename)
            job_id = str(uuid.uuid4())

            tmp_data = {
                "selection": selection,
                "input_path": input_path,
                "output_path": "",
            }
            tmp_file = os.path.join(settings.MEDIA_ROOT, "uploads/tmp", f"{job_id}.json")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(tmp_data, f)

            request.session["job_id"] = job_id
            return redirect("processing")
    else:
        form = UploadForm()

    return render(request, "products/upload_photo.html", {"form": form, "selection": selection})


# ----------------------------------------------------------
# Procesamiento de imagen con OpenAI
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
        job_data = json.load(f)

    input_path = job_data.get("input_path")
    selection = job_data.get("selection", {})

    # Determinar prompt según la selección
    prompt = f"Genera una imagen relacionada con {selection.get('categoria', 'producto')} en fondo {selection.get('color_fondo', 'blanco')}."

    # Llamada a la API de OpenAI para edición de imagen
    try:
        output_image = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024",
        )

        image_base64 = output_image.data[0].b64_json
        output_data = np.frombuffer(bytes(image_base64, "utf-8"), dtype=np.uint8)
        output_path = os.path.join(settings.MEDIA_ROOT, "uploads/output", f"{job_id}.png")
        with open(output_path, "wb") as f:
            f.write(output_data)

        job_data["output_path"] = output_path
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(job_data, f)

        request.session["job_id"] = job_id
        return redirect("result")
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return render(request, "products/error.html", {"message": str(e)})


# ----------------------------------------------------------
# Resultado final
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
        job_data = json.load(f)

    output_path = job_data.get("output_path")
    selection = job_data.get("selection", {})

    return render(
        request,
        "products/result.html",
        {"output_path": output_path, "selection": selection},
    )
