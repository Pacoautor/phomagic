import os
from django.conf import settings
from django.shortcuts import render

def select_category(request):
    """
    Lee dinámicamente todas las categorías y subcategorías de media/lineas
    """
    lineas_root = os.path.join(settings.BASE_DIR, 'media', 'lineas')
    categorias = []

    if os.path.exists(lineas_root):
        for categoria in sorted(os.listdir(lineas_root)):
            categoria_path = os.path.join(lineas_root, categoria)
            if os.path.isdir(categoria_path):
                subcategorias = []
                for sub in sorted(os.listdir(categoria_path)):
                    sub_path = os.path.join(categoria_path, sub)
                    if os.path.isdir(sub_path):
                        vistas = []
                        for archivo in os.listdir(sub_path):
                            if archivo.endswith('.png'):
                                vistas.append({
                                    "nombre": os.path.splitext(archivo)[0],
                                    "imagen": f"/media/lineas/{categoria}/{sub}/{archivo}"
                                })
                        subcategorias.append({
                            "nombre": sub,
                            "vistas": vistas
                        })
                categorias.append({
                    "nombre": categoria,
                    "subcategorias": subcategorias
                })

    return render(request, "select_category.html", {"categorias": categorias})





def select_view(request):
    """
    Muestra las miniaturas PNG dentro de una categoría seleccionada.
    """
    categoria = request.GET.get("categoria")
    if not categoria:
        return redirect("select_category")

    base_path = Path(settings.MEDIA_ROOT) / "lineas" / categoria
    if not base_path.exists():
        return render(request, "error.html", {"error": f"No se encontró la categoría '{categoria}'."})

    vistas = sorted([f.name for f in base_path.glob("*.png")])
    if not vistas:
        return render(request, "upload_photo.html", {
            "categoria": categoria,
            "vistas": [],
            "error": "No se encontraron vistas en /media/lineas/."
        })

    request.session["selection"] = categoria
    return render(request, "upload_photo.html", {"categoria": categoria, "vistas": vistas})


def set_selected_view(request):
    """
    Guarda la vista seleccionada por el usuario en la sesión.
    """
    selected_view = request.GET.get("view")
    if selected_view:
        request.session["selected_view"] = selected_view
        return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "error", "message": "Vista no válida"})


def upload_photo(request):
    """
    Permite subir y procesar una imagen.
    """
    categoria = request.session.get("selection")
    selected_view = request.session.get("selected_view")

    if request.method == "POST":
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return render(request, "upload_photo.html", {
                "error": "No se seleccionó ningún archivo.",
                "categoria": categoria,
                "vistas": _get_vistas(categoria)
            })

        upload_dir = Path(settings.MEDIA_ROOT) / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / uploaded_file.name

        with default_storage.open(str(file_path), 'wb+') as dest:
            for chunk in uploaded_file.chunks():
                dest.write(chunk)

        request.session["uploaded_file_url"] = f"/media/uploads/{uploaded_file.name}"
        return redirect("processing")

    vistas = _get_vistas(categoria)
    return render(request, "upload_photo.html", {"categoria": categoria, "vistas": vistas})


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


def _get_vistas(categoria):
    if not categoria:
        return []
    path = Path(settings.MEDIA_ROOT) / "lineas" / categoria
    if not path.exists():
        return []
    return sorted([f.name for f in path.glob("*.png")])
