from __future__ import annotations

import base64
import io
import os
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render, redirect

from PIL import Image, ImageOps

from .models import Category, Subcategory, ViewOption

# --- (Opcional) Cliente OpenAI si tienes OPENAI_API_KEY configurada ---
try:
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception:
    openai_client = None


# -------- Helpers de rutas/archivos --------
def _media_url(rel_path: str) -> str:
    """
    Convierte una ruta relativa dentro de MEDIA a URL accesible por el navegador.
    """
    rel_path = rel_path.replace("\\", "/")
    base = settings.MEDIA_URL.rstrip("/")
    return f"{base}/{rel_path.lstrip('/')}"


def _media_abs(rel_path: str) -> Path:
    """
    Devuelve ruta absoluta en MEDIA_ROOT para una ruta relativa dada.
    """
    return Path(settings.MEDIA_ROOT) / rel_path


def _ensure_dir(p: Path):
    """
    Crea el directorio padre si no existe.
    """
    p.parent.mkdir(parents=True, exist_ok=True)


def _add_white_border(in_path: Path, out_path: Path, border_px: int = 50) -> None:
    """
    Abre la imagen 'in_path', añade borde blanco uniforme y guarda en 'out_path'.
    """
    with Image.open(in_path) as im:
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGB")
        padded = ImageOps.expand(im, border=border_px, fill="white")
        _ensure_dir(out_path)
        padded.save(out_path, format="JPEG", quality=92, optimize=True)


# --------- VISTAS PÚBLICAS ---------

def home(request):
    """
    Portada con el grid de categorías.
    """
    # Si tu modelo tuviera un campo 'ordering_index' lo podrías usar aquí.
    categories = Category.objects.all().order_by("name")
    return render(request, "home.html", {"categories": categories})


def category_detail(request, category_slug: str):
    """
    Página de detalle de categoría mostrando sus subcategorías.
    Ruta: /c/<slug:category_slug>/
    """
    # Intento por slug (lo normal en producción)
    try:
        category = Category.objects.get(slug=category_slug)
    except Category.DoesNotExist:
        # Fallback raro por si no existe slug en tus datos locales
        category = get_object_or_404(Category, name__iexact=category_slug.replace("-", " "))
    subcategories = Subcategory.objects.filter(category=category).order_by("name")
    return render(
        request,
        "products/category_detail.html",
        {"category": category, "subcategories": subcategories},
    )


def subcategory_detail(request, category_id: int):
    """
    Lista las subcategorías de una categoría por id (si usas esta ruta).
    Ruta: /s/<int:category_id>/
    """
    category = get_object_or_404(Category, id=category_id)
    subcategories = Subcategory.objects.filter(category=category).order_by("name")
    return render(
        request,
        "products/subcategory_detail.html",
        {"category": category, "subcategories": subcategories},
    )


def view_options(request, subcategory_id: int):
    """
    Lista las opciones de vista (ViewOption) de una subcategoría concreta.
    Ruta: /v/<int:subcategory_id>/
    """
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    options = ViewOption.objects.filter(subcategory=subcategory).order_by("name")
    return render(
        request,
        "products/view_options.html",
        {"subcategory": subcategory, "options": options},
    )


# --------- GENERAR IMAGEN (usa SIEMPRE la foto del cliente) ---------

def generate_photo(request, subcategory_id: int, view_id: int):
    """
    GET  -> formulario para subir foto del cliente.
    POST -> usa SIEMPRE la foto del cliente + prompt oculto de la vista para generar,
            guarda resultado y AÑADE 50px BLANCOS alrededor antes de mostrar.
    Ruta: /g/<int:subcategory_id>/<int:view_id>/
    """
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    category = subcategory.category
    viewopt = get_object_or_404(ViewOption, id=view_id, subcategory=subcategory)

    if request.method == "GET":
        return render(
            request,
            "products/upload_photo.html",
            {
                "category": category,
                "subcategory": subcategory,
                "viewoption": viewopt,
            },
        )

    # ---- POST (generar) ----
    photo = request.FILES.get("photo")
    if not photo:
        return HttpResponseBadRequest("Falta la imagen del cliente.")

    # 1) Guardamos la imagen subida en MEDIA: uploads/input/
    original_name = Path(photo.name).name
    input_rel = f"uploads/input/{original_name}"
    input_abs = _media_abs(input_rel)
    _ensure_dir(input_abs)
    with default_storage.open(str(input_rel), "wb") as dst:
        for chunk in photo.chunks():
            dst.write(chunk)

    # 2) Prompt oculto (NO se enseña en la plantilla)
    prompt = (
        getattr(viewopt, "prompt_main", None)
        or getattr(viewopt, "prompt", None)
        or "Mejora fotográfica del producto manteniendo la identidad del sujeto"
    )

    # 3) Generar/editar imagen con la foto del cliente
    output_basename = f"gen_{subcategory.id}_{viewopt.id}_{Path(original_name).stem}.jpg"
    output_rel = f"uploads/output/{output_basename}"
    output_abs = _media_abs(output_rel)
    _ensure_dir(output_abs)

    generated_ok = False

    if openai_client is not None:
        try:
            # Lee bytes de la imagen base (cliente)
            with default_storage.open(str(input_rel), "rb") as f:
                img_bytes = f.read()

            # --- Ajusta este bloque al proveedor/modelo que uses ---
            # Ejemplo con OpenAI "images.edits" (usa la imagen del cliente como base).
            res = openai_client.images.edits(
                model="gpt-image-1",
                prompt=prompt,
                image=[("image", ("input.jpg", img_bytes, "image/jpeg"))],
                size="1024x1024",
                n=1,
                response_format="b64_json",
            )
            b64 = res.data[0].b64_json
            raw = base64.b64decode(b64)
            with Image.open(io.BytesIO(raw)) as im:
                if im.mode in ("RGBA", "LA", "P"):
                    im = im.convert("RGB")
                im.save(output_abs, format="JPEG", quality=92, optimize=True)
            generated_ok = True
        except Exception:
            # Respaldo: si falla la IA, dejamos pasar la imagen subida
            try:
                if "img_bytes" in locals():
                    default_storage.save(str(output_rel), ContentFile(img_bytes))
                else:
                    with default_storage.open(str(input_rel), "rb") as fsrc:
                        default_storage.save(str(output_rel), ContentFile(fsrc.read()))
                generated_ok = True
            except Exception:
                pass
    else:
        # Sin cliente IA disponible: copia directa (para no romper UX)
        with default_storage.open(str(input_rel), "rb") as fsrc:
            default_storage.save(str(output_rel), ContentFile(fsrc.read()))
        generated_ok = True

    # 4) Añadir borde blanco de 50px SIEMPRE al resultado
    padded_rel = f"uploads/output/padded_{output_basename}"
    padded_abs = _media_abs(padded_rel)
    try:
        _add_white_border(output_abs, padded_abs, border_px=50)
        final_rel = padded_rel
    except Exception:
        final_rel = output_rel  # si fallara el padding, mostramos la generada sin borde

    final_url = _media_url(final_rel)

    # 5) Render
    return render(
        request,
        "products/upload_photo.html",
        {
            "category": category,
            "subcategory": subcategory,
            "viewoption": viewopt,
            "final_url": final_url,  # la plantilla lo detecta y lo muestra
        },
    )
