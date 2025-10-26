# products/views.py
import os
import json
import uuid
import logging
from pathlib import Path

from django.conf import settings
from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django import forms

# Formulario de la página 1 (el que ya tienes en products/forms.py)
from .forms import SelectCategoryForm

logger = logging.getLogger("django")

# Formulario mínimo de subida (lo definimos aquí para no tocar forms.py)
class UploadForm(forms.Form):
    image = forms.ImageField(label="Selecciona una imagen")


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
# Paso 3: procesamiento (lazy OpenAI y fallback seguro)
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

    selection = job.get("selection", {})
    prompt = f"Genera una imagen relacionada con {selection.get('categoria', 'producto')} en fondo {selection.get('color_fondo', 'blanco')}."
    output_path = os.path.join(settings.MEDIA_ROOT, "uploads/output", f"{job_id}.png")

    # Intento de usar OpenAI SOLO aquí (nunca en import del módulo)
    try:
        from openai import OpenAI  # import local
        api_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY no está configurada")

        client = OpenAI(api_key=api_key)
        # Si quieres usar edición real, aquí iría tu llamada. Dejo un placeholder:
        # result = client.images.generate(model="gpt-image-1", prompt=prompt, size="1024x1024")
        # with open(output_path, "wb") as f: f.write(base64.b64decode(result.data[0].b64_json))

        # Placeholder para no romper: crea un PNG mínimo válido
        _write_minimal_png(output_path)

    except Exception as e:
        logger.error(f"[processing] Fallback por error en OpenAI: {e}")
        # Fallback seguro: generamos un PNG mínimo para que el flujo complete
        _write_minimal_png(output_path)

    # Guardamos la salida y seguimos
    job["output_path"] = output_path
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(job, f)

    request.session["job_id"] = job_id
    request.session.modified = True
    return redirect("result")


def _write_minimal_png(path: str):
    """
    Escribe un PNG válido mínimo (1x1 transparente) para pruebas de flujo.
    """
    try:
        from PIL import Image
        img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        img.save(path, format="PNG")
    except Exception as e:
        # Último recurso: cabecera PNG + chunk IEND mínimo (no todos los visores lo aceptan)
        logger.warning(f"No se pudo escribir PNG con PIL ({e}); usando fallback binario mínimo.")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(
                b"\x89PNG\r\n\x1a\n"
                b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                b"\x00\x00\x00\x0AIEND\xaeB`\x82"
            )


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
