import os
from pathlib import Path
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse


# --------------------------------------------------------
# Selección de categoría
# --------------------------------------------------------
def select_category(request):
    """
    Muestra todas las categorías disponibles dentro de media/lineas.
    """
    base_path = Path(settings.MEDIA_ROOT) / "lineas"
    categorias = []

    if base_path.exists():
        for folder in sorted(base_path.iterdir()):
            if folder.is_dir():
                categorias.append(folder.name)

    return render(request, "select_category.html", {"categorias": categorias})


# --------------------------------------------------------
# Selección de vista
# --------------------------------------------------------
def select_view(request):
    """
    Muestra todas las subcategorías y vistas dentro de una categoría seleccionada.
    """
    categoria = request.GET.get("categoria")
    if not categoria:
        return redirect("select_category")

    base_path = Path(settings.MEDIA_ROOT) / "lineas" / categoria

    if not base_path.exists():
        return render(request, "upload_photo.html", {
            "categoria": categoria,
            "vistas": [],
            "error": f"No se encontró la categoría '{categoria}'."
        })

    # Buscar recursivamente imágenes .png
    vistas = []
    for subdir, dirs, files in os.walk(base_path):
        for file in files:
            if file.lower().endswith(".png"):
                relative_path = os.path.relpath(os.path.join(subdir, file), base_path)
                vistas.append(relative_path.replace("\\", "/"))

    if not vistas:
        return render(request, "upload_photo.html", {
            "categoria": categoria,
            "vistas": [],
            "error": "No se encontraron vistas dentro de la categoría seleccionada."
        })

    # Guardamos la categoría actual en sesión
    request.session["selection"] = categoria
    return render(request, "upload_photo.html", {"categoria": categoria, "vistas": vistas})


# --------------------------------------------------------
# Guardar vista seleccionada
# --------------------------------------------------------
def set_selected_view(request):
    """
    Guarda la vista seleccionada por el usuario en la sesión.
    """
    selected_view = request.GET.get("view")
    if selected_view:
        request.session["selected_view"] = selected_view
        return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "error", "message": "Vista no válida"})


# --------------------------------------------------------
# Subida y procesamiento de imagen
# --------------------------------------------------------
def upload_photo(request):
    """
    Maneja la subida de imagen y conserva la categoría y vista seleccionada.
    """
    categoria = request.session.get("selection") or request.GET.get("categoria")
    vista = request.session.get("selected_view")

    if request.method == "POST":
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return render(request, "upload_photo.html", {
                "error": "Debes seleccionar una imagen.",
                "categoria": categoria,
                "vistas": [],
            })

        # Guarda la imagen subida en una carpeta temporal
        upload_path = Path(settings.MEDIA_ROOT) / "uploads" / "input"
        upload_path.mkdir(parents=True, exist_ok=True)
        file_path = upload_path / uploaded_file.name
        with open(file_path, "wb+") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        # Guardamos la ruta del archivo subido en la sesión
        request.session["uploaded_file_url"] = str(file_path)

        # Confirmación visual
        return render(request, "upload_photo.html", {
            "success": f"Imagen '{uploaded_file.name}' subida correctamente.",
            "categoria": categoria,
            "vistas": get_vistas(categoria),
        })

    # Si llega por GET, mostrar vistas disponibles
    vistas = get_vistas(categoria)
    return render(request, "upload_photo.html", {"categoria": categoria, "vistas": vistas})


# --------------------------------------------------------
# Página de procesamiento (placeholder para IA)
# --------------------------------------------------------
def processing(request):
    """
    Simula el procesamiento de la imagen con la vista seleccionada.
    """
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


# --------------------------------------------------------
# Función auxiliar: obtener vistas (.png)
# --------------------------------------------------------
def get_vistas(categoria):
    """
    Devuelve todas las vistas (.png) dentro de una categoría o subcategoría.
    """
    if not categoria:
        return []

    path = Path(settings.MEDIA_ROOT) / "lineas" / categoria
    if not path.exists():
        return []

    vistas = []
    for subdir, dirs, files in os.walk(path):
        for file in files:
            if file.lower().endswith(".png"):
                relative = os.path.relpath(os.path.join(subdir, file), path)
                vistas.append(relative.replace("\\", "/"))
    return sorted(vistas)
