from django.contrib import messages
from django.conf import settings
from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse

from pathlib import Path
import os
import logging
from PIL import Image

logger = logging.getLogger("django")


def ensure_dirs():
    """Verifica que la carpeta 'lineas' exista."""
    base_path = Path(settings.MEDIA_ROOT) / "lineas"
    base_path.mkdir(parents=True, exist_ok=True)
    return base_path


def _find_assets():
    """
    Escanea las carpetas dentro de /media/lineas y devuelve:
    {
        "categoria": "Calzado",
        "vistas": [
            {"nombre": "vista1", "thumb": "/media/lineas/Calzado/vista1.png"},
            {"nombre": "vista2", "thumb": "/media/lineas/Calzado/vista2.png"},
        ]
    }
    """
    base_path = ensure_dirs()
    categorias = []

    for categoria_dir in sorted(base_path.iterdir()):
        if not categoria_dir.is_dir():
            continue

        vistas = []
        for archivo in categoria_dir.iterdir():
            if archivo.suffix.lower() == ".png":
                vistas.append({
                    "nombre": archivo.stem,
                    "thumb": f"{settings.MEDIA_URL}lineas/{categoria_dir.name}/{archivo.name}"
                })

        if vistas:
            categorias.append({
                "categoria": categoria_dir.name,
                "vistas": vistas
            })

    logger.info(f"Categorías detectadas: {len(categorias)}")
    return categorias


def upload_photo(request):
    """Pantalla principal: selección de categoría/vista + subida de imagen."""
    categorias = _find_assets()
    selected_view = request.session.get("selected_view")
    selected_category = request.session.get("selected_category")

    if request.method == "POST":
        uploaded_file = request.FILES.get("image")
        selected_view = request.POST.get("selected_view")
        selected_category = request.POST.get("selected_category")

        if not uploaded_file:
            messages.warning(request, "Por favor, selecciona una imagen antes de continuar.")
            return redirect("upload_photo")

        if not selected_category or not selected_view:
            messages.warning(request, "Selecciona una categoría y una vista antes de subir la imagen.")
            return redirect("upload_photo")

        fs = FileSystemStorage(location=Path(settings.MEDIA_ROOT) / "tmp")
        filename = fs.save(uploaded_file.name, uploaded_file)
        uploaded_path = str(Path(fs.location) / filename)

        request.session["uploaded_file_path"] = uploaded_path
        request.session["selected_category"] = selected_category
        request.session["selected_view"] = selected_view

        return redirect("processing")

    return render(request, "upload_photo.html", {
        "categorias": categorias,
        "selected_category": selected_category,
        "selected_view": selected_view,
    })


def processing(request):
    """Procesa la imagen subida según la categoría y vista seleccionadas."""
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        return render(request, "error.html", {"error": "Falta la clave de API de OpenAI."})

    try:
        uploaded_path = request.session.get("uploaded_file_path")
        selected_view = request.session.get("selected_view")
        selected_category = request.session.get("selected_category")

        if not uploaded_path or not os.path.exists(uploaded_path):
            return render(request, "error.html", {"error": "No se encontró la imagen subida."})
        if not selected_view or not selected_category:
            return render(request, "error.html", {"error": "Faltan datos de selección."})

        logger.info(f"Procesando imagen con {selected_category} / {selected_view}")

        # Simulación del resultado (por ahora)
        result_url = "/media/results/ejemplo_resultado.png"

        return render(request, "result.html", {
            "result_url": result_url,
            "selected_category": selected_category,
            "selected_view": selected_view,
        })

    except Exception as e:
        logger.error(f"Error al procesar imagen: {e}")
        return render(request, "error.html", {"error": f"Error: {e}"})
