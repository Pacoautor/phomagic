import os
from pathlib import Path
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.files.storage import default_storage

# ============================================================
# 🧩 1. SELECCIÓN DE CATEGORÍA
# ============================================================

def select_category(request):
    """
    Muestra todas las categorías (carpetas dentro de media/lineas).
    """
    base_path = Path(settings.MEDIA_ROOT) / "lineas"
    if not base_path.exists():
        return render(request, "error.html", {"error": "No se encontró la carpeta 'media/lineas'."})

    categorias = [d.name for d in base_path.iterdir() if d.is_dir()]
    return render(request, "select_category.html", {"categorias": categorias})


# ============================================================
# 🧩 2. SELECCIÓN DE VISTA DENTRO DE UNA CATEGORÍA
# ============================================================

def select_view(request):
    """
    Carga las vistas (miniaturas PNG) de una categoría seleccionada.
    """
    categoria = request.GET.get("categoria")
    if not categoria:
        return redirect("select_category")

    request.session["selection"] = categoria
    category_path = Path(settings.MEDIA_ROOT) / "lineas" / categoria

    # Buscar vistas PNG dentro de la categoría
    vistas = sorted([f.name for f in category_path.glob("*.png")])
    return render(request, "upload_photo.html", {"categoria": categoria, "vistas": vistas})


# ============================================================
# 🧩 3. SELECCIONAR UNA MINIATURA
# ============================================================

def set_selected_view(request):
    """
    Guarda en la sesión la vista seleccionada por el usuario.
    """
    selected_view = request.GET.get("view")
    if selected_view:
        request.session["selected_view"] = selected_view
        return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "error", "message": "Vista no válida"})


# ============================================================
# 🧩 4. SUBIR IMAGEN Y MOSTRAR FORMULARIO DE PROCESAMIENTO
# ============================================================

def upload_photo(request):
    """
    Muestra el formulario de subida y procesamiento de imagen.
    """
    categoria = request.session.get("selection")
    selected_view = request.session.get("selected_view")

    if request.method == "POST":
        uploaded_file = request.FILES.get("file")
        if not categoria or not selected_view:
            return render(request, "upload_photo.html", {
                "error": "Selecciona una categoría y una vista antes de subir la imagen.",
                "categoria": categoria,
                "vistas": _get_vistas(categoria)
            })

        if uploaded_file:
            upload_dir = Path(settings.MEDIA_ROOT) / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            file_path = upload_dir / uploaded_file.name
            with default_storage.open(str(file_path), 'wb+') as dest:
                for chunk in uploaded_file.chunks():
                    dest.write(chunk)

            request.session["uploaded_file_url"] = f"/media/uploads/{uploaded_file.name}"
            return redirect("processing")

    vistas = _get_vistas(categoria) if categoria else []
    return render(request, "upload_photo.html", {"categoria": categoria, "vistas": vistas})


# ============================================================
# 🧩 5. PROCESAMIENTO FINAL
# ============================================================

def processing(request):
    categoria = request.session.get("selection")
    selected_view = request.session.get("selected_view")
    uploaded_file_url = request.session.get("uploaded_file_url")

    if not categoria or not selected_view or not uploaded_file_url:
        return render(request, "error.html", {"error": "Faltan datos para procesar la imagen."})

    return render(request, "processing.html", {
        "categoria": categoria,
        "selected_view": selected_view,
        "uploaded_file_url": uploaded_file_url,
    })


# ============================================================
# 🧩 6. FUNCIÓN AUXILIAR
# ============================================================

def _get_vistas(categoria):
    """
    Devuelve la lista de vistas PNG disponibles en una categoría.
    """
    if not categoria:
        return []
    category_path = Path(settings.MEDIA_ROOT) / "lineas" / categoria
    if not category_path.exists():
        return []
    return sorted([f.name for f in category_path.glob("*.png")])

