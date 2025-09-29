from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.text import slugify
from pathlib import Path

from .models import Category, Subcategory, ViewOption


def home(request):
    """Lista de categorías."""
    categories = Category.objects.all().order_by("name")
    return render(request, "products/category_list.html", {"categories": categories})


def category_detail(request, category_slug):
    """Lista de subcategorías de una categoría."""
    category = get_object_or_404(Category, slug=category_slug)
    subcategories = Subcategory.objects.filter(category=category).order_by("name")
    return render(
        request,
        "products/subcategory_list.html",
        {"category": category, "subcategories": subcategories},
    )


def view_options(request, subcategory_id):
    """Lista de vistas disponibles para una subcategoría."""
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    options = ViewOption.objects.filter(subcategory=subcategory).order_by("name")
    return render(
        request,
        "products/view_options.html",
        {"subcategory": subcategory, "options": options},
    )


@login_required
def generate_photo(request, subcategory_id, view_id):
    """
    Pantalla de subida + resultado.
    Si hay OpenAI más adelante, aquí se invoca la edición *sobre la foto subida del cliente*.
    Mientras tanto, mostramos la foto subida como resultado para no romper el flujo.
    """
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    viewopt = get_object_or_404(ViewOption, id=view_id, subcategory=subcategory)

    result_url = None
    error_msg = None

    if request.method == "POST" and request.FILES.get("photo"):
        # Guardar la imagen subida en MEDIA/generated/...
        photo = request.FILES["photo"]
        # base_id: solo con datos seguros (evitamos subcategory.slug por si no existe)
        base_id = f"{slugify(subcategory.category.name)}_{slugify(subcategory.name)}_{viewopt.id}"
        original_stem = Path(photo.name).stem
        out_name = f"generated/{base_id}_{slugify(original_stem)}{Path(photo.name).suffix}"

        try:
            saved_path = default_storage.save(out_name, ContentFile(photo.read()))
            result_url = default_storage.url(saved_path)

            # >>> Aquí, cuando quieras, haces la llamada a OpenAI EDIT para sustituir result_url
            # por la URL del resultado generado. Si falla, mostramos la subida para no romper.

        except Exception as e:
            error_msg = f"No se pudo procesar la imagen: {e}"

    context = {
        "subcategory": subcategory,
        "viewoption": viewopt,
        "result_url": result_url,   # si None, se muestra el formulario
        "error_msg": error_msg,
    }
    return render(request, "products/upload_photo.html", context)
