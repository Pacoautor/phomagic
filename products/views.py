import os
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage

# Ruta base donde están las líneas (categorías principales)
LINEAS_ROOT = os.path.join(settings.MEDIA_ROOT, "lineas")

# Variable global simple (temporal, idealmente mover a sesión)
USER_SELECTION = {}


def select_category(request):
    """Muestra las categorías principales dentro de media/lineas/"""
    try:
        categories = sorted([
            folder for folder in os.listdir(LINEAS_ROOT)
            if os.path.isdir(os.path.join(LINEAS_ROOT, folder))
        ])
    except FileNotFoundError:
        categories = []

    return render(request, "select_category.html", {"categories": categories})


def select_subcategory(request, category):
    """Muestra las subcategorías dentro de una categoría seleccionada"""
    category_path = os.path.join(LINEAS_ROOT, category)
    try:
        subcategories = sorted([
            folder for folder in os.listdir(category_path)
            if os.path.isdir(os.path.join(category_path, folder))
        ])
    except FileNotFoundError:
        subcategories = []

    return render(request, "select_subcategory.html", {
        "category": category,
        "subcategories": subcategories,
    })


def select_view(request, category, subcategory):
    """Muestra las vistas (miniaturas PNG y prompts DOCX)"""
    subcat_path = os.path.join(LINEAS_ROOT, category, subcategory)
    views = []

    try:
        for file in sorted(os.listdir(subcat_path)):
            if file.lower().endswith(".png"):
                view_number = os.path.splitext(file)[0]
                doc_path = os.path.join(subcat_path, f"{view_number}.docx")
                if os.path.exists(doc_path):
                    views.append({
                        "image": os.path.join("media/lineas", category, subcategory, file),
                        "prompt": os.path.join("media/lineas", category, subcategory, f"{view_number}.docx"),
                        "name": view_number,
                    })
    except FileNotFoundError:
        pass

    return render(request, "upload_photo.html", {
        "category": category,
        "subcategory": subcategory,
        "views": views
    })


def upload_photo(request):
    """Sube una foto y guarda la selección del usuario"""
    if request.method == "POST":
        category = request.POST.get("category")
        subcategory = request.POST.get("subcategory")
        selected_view = request.POST.get("selected_view")
        uploaded_file = request.FILES.get("photo")

        if not (category and subcategory and selected_view and uploaded_file):
            return render(request, "error.html", {
                "error": "Faltan datos o no se ha seleccionado vista o imagen."
            })

        fs = FileSystemStorage()
        filename = fs.save(uploaded_file.name, uploaded_file)
        USER_SELECTION["image_path"] = fs.url(filename)
        USER_SELECTION["category"] = category
        USER_SELECTION["subcategory"] = subcategory
        USER_SELECTION["view"] = selected_view

        return redirect("processing")

    return redirect("select_category")


def processing(request):
    """Procesa la imagen con el prompt de la vista seleccionada"""
    user_data = USER_SELECTION.copy()
    image_path = user_data.get("image_path")
    view_name = user_data.get("view")
    category = user_data.get("category")
    subcategory = user_data.get("subcategory")

    if not all([image_path, view_name, category, subcategory]):
        return render(request, "error.html", {"error": "No se encontró la selección completa."})

    # Ruta al prompt de la vista seleccionada
    prompt_path = os.path.join(settings.MEDIA_ROOT, "lineas", category, subcategory, f"{view_name}.docx")

    if not os.path.exists(prompt_path):
        return render(request, "error.html", {"error": f"No se encontró el prompt: {prompt_path}"})

    # Simulación del procesamiento
    result_image = image_path  # en el futuro: resultado real del API

    return render(request, "processing.html", {
        "image_url": result_image,
        "category": category,
        "subcategory": subcategory,
        "view": view_name,
    })
