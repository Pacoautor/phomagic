from django.contrib import messages
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage

import os
import json
import logging
from pathlib import Path
from PIL import Image
import openai

logger = logging.getLogger("django")


def ensure_dirs():
    """Crea las carpetas necesarias si no existen."""
    base_dirs = [
        Path(settings.MEDIA_ROOT) / "uploads",
        Path(settings.MEDIA_ROOT) / "uploads" / "tmp",
        Path(settings.MEDIA_ROOT) / "uploads" / "views",
        Path(settings.MEDIA_ROOT) / "results"
    ]
    for d in base_dirs:
        d.mkdir(parents=True, exist_ok=True)


def _find_assets():
    """Busca las vistas disponibles con miniaturas."""
    assets_path = Path(settings.MEDIA_ROOT) / "uploads" / "views"
    assets = []
    if assets_path.exists():
        for folder in assets_path.iterdir():
            if folder.is_dir():
                thumb = None
                for f in folder.iterdir():
                    if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                        thumb = f"{settings.MEDIA_URL}uploads/views/{folder.name}/{f.name}"
                        break
                assets.append({
                    "name": folder.name,
                    "thumb": thumb or f"{settings.STATIC_URL}img/no-thumb.png"
                })
    return assets


def upload_photo(request):
    """Vista principal: muestra selector de vistas y subida de imagen."""
    ensure_dirs()
    assets = _find_assets()
    selected_view = request.session.get("selected_view", None)

    if request.method == "POST":
        uploaded_file = request.FILES.get("image")
        selected_view = request.POST.get("selected_view")

        if not uploaded_file:
            messages.warning(request, "Por favor, selecciona una imagen antes de continuar.")
            return redirect("upload_photo")

        if not selected_view:
            messages.warning(request, "Selecciona una vista antes de subir la imagen.")
            return redirect("upload_photo")

        fs = FileSystemStorage(location=Path(settings.MEDIA_ROOT) / "uploads" / "tmp")
        filename = fs.save(uploaded_file.name, uploaded_file)
        uploaded_file_path = str(Path(fs.location) / filename)

        request.session["uploaded_file_path"] = uploaded_file_path
        request.session["selected_view"] = selected_view

        return redirect("processing")

    return render(request, "upload_photo.html", {
        "assets": assets,
        "selected_view": selected_view,
    })


def processing(request):
    """Procesa la imagen subida con la vista seleccionada."""
    ensure_dirs()
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return render(request, "error.html", {"error": "Falta la clave de API de OpenAI."})

    try:
        uploaded_file_path = request.session.get("uploaded_file_path")
        selected_view = request.session.get("selected_view")

        if not uploaded_file_path or not os.path.exists(uploaded_file_path):
            return render(request, "error.html", {"error": "No se encontró la imagen subida."})
        if not selected_view:
            return render(request, "error.html", {"error": "No se seleccionó ninguna vista."})

        img = Image.open(uploaded_file_path)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        rgba_path = str(Path(uploaded_file_path).with_suffix(".png"))
        img.save(rgba_path, "PNG")

        logger.info(f"Procesando imagen con la vista: {selected_view}")

        result_url = "/media/results/fake_result.png"

        return render(request, "result.html", {
            "result_url": result_url,
            "selected_view": selected_view
        })

    except Exception as e:
        logger.error(f"Error al procesar imagen: {e}")
        return render(request, "error.html", {"error": f"Error al procesar la imagen: {e}"})
