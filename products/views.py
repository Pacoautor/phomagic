# products/views.py
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from .models import Category, Subcategory, ViewOption, GeneratedImage


def home(request):
    """
    Portada con el listado de categorías.
    """
    categories = Category.objects.all().order_by("name")
    # Si ya tienes templates/home.html, úsalo; si no, usamos uno de fallback simple.
    try:
        return render(request, "home.html", {"categories": categories})
    except Exception:
        # Fallback mínimo para no romper mientras haces migraciones
        items = "<br>".join([c.name for c in categories]) or "(sin categorías)"
        return HttpResponse(f"<h1>Categorías</h1><div>{items}</div>")


def category_detail(request, category_slug=None, category_id=None):
    """
    Detalle de categoría con subcategorías.
    Admite id o slug (usa lo que tengas en tu BD).
    """
    category = None
    if category_id:
        category = get_object_or_404(Category, id=category_id)
    elif category_slug and hasattr(Category, "slug"):
        category = get_object_or_404(Category, slug=category_slug)
    else:
        # Si no tienes slug en Category, intenta por nombre en mayúsculas que usas en la BD
        category = get_object_or_404(Category, name__iexact=category_slug or "")

    subcats = Subcategory.objects.filter(category=category).order_by("name")
    # Si existe plantilla, úsala
    template_candidates = [
        "products/category_detail.html",
        "category_detail.html",
        "home.html",  # al menos muestra algo con tu base
    ]
    context = {"category": category, "subcategories": subcats}
    for t in template_candidates:
        try:
            return render(request, t, context)
        except Exception:
            continue
    # Fallback
    items = "<br>".join([s.name for s in subcats]) or "(sin subcategorías)"
    return HttpResponse(f"<h1>{category.name}</h1><div>{items}</div>")


def view_options(request, subcategory_id):
    """
    Lista de vistas disponibles para una subcategoría.
    """
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    views_qs = ViewOption.objects.filter(subcategory=subcategory).order_by("name")
    # Intenta tu plantilla si existe
    template_candidates = [
        "products/view_options.html",
        "view_options.html",
        "home.html",
    ]
    context = {"subcategory": subcategory, "view_options": views_qs}
    for t in template_candidates:
        try:
            return render(request, t, context)
        except Exception:
            continue
    # Fallback
    items = "<br>".join([v.name for v in views_qs]) or "(sin vistas)"
    return HttpResponse(f"<h1>{subcategory}</h1><div>{items}</div>")


@login_required
def generate_photo(request, subcategory_id, view_id):
    """
    Vista de generación. Dejo un cuerpo mínimo para no romper migraciones ni despliegues.
    Cuando esté todo migrado, ya conectamos tu flujo de subida y edición.
    """
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    viewopt = get_object_or_404(ViewOption, id=view_id, subcategory=subcategory)

    # Si tienes la plantilla products/upload_photo.html se usará;
    # si no, devolvemos un formulario mínimo de fallback.
    context = {"subcategory": subcategory, "viewoption": viewopt}
    try:
        return render(request, "products/upload_photo.html", context)
    except Exception:
        html = f"""
        <h1>Generar imagen</h1>
        <p>Subcategoría: {subcategory}</p>
        <p>Vista: {viewopt.name}</p>
        <form method="post" enctype="multipart/form-data">
          <input type="hidden" name="csrfmiddlewaretoken" value="">
          <input type="file" name="photo" accept="image/*">
          <button type="submit">Subir</button>
        </form>
        """
        return HttpResponse(html)
