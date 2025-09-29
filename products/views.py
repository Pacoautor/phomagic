
import base64
import os
from pathlib import Path

import requests
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404, render
from django.utils.text import slugify

from .models import Category, Subcategory, ViewOption


# ---------- P R O M P T S  I N T E R N O S ----------
# NO se muestran en pantallas. Ajusta a tu gusto.
def get_prompt_for(viewopt: ViewOption) -> str:
    """
    Devuelve el prompt interno de edición para la vista concreta.
    Personaliza por viewopt.id o por nombre.
    """
    # Ejemplos; cambia/añade según tus vistas:
    MAP_ID = {
        # viewopt.id : "prompt"
        # 1: "producto sobre fondo blanco, luz suave de estudio, sombras suaves realistas, estilo catálogo e-commerce",
        # 2: "maniquí invisible, recorte limpio, fondo #FFFFFF, alto contraste, detalle de costuras",
        # 3: "doblada con pliegues naturales, fondo neutro, composición centrada, estilo lookbook minimalista",
    }

    if viewopt.id in MAP_ID:
        return MAP_ID[viewopt.id]

    # Fallback por nombre (menos fiable, pero útil si no has llenado MAP_ID)
    name = (viewopt.name or "").lower()
    if "maniquí" in name:
        return "maniquí invisible, recorte perfecto, fondo blanco puro, iluminación uniforme de estudio"
    if "plegada" in name or "doblada" in name:
        return "prenda doblada con pliegues naturales, fondo blanco, sombras suaves realistas, estilo catálogo"
    if "extendida" in name:
        return "prenda extendida totalmente visible, fondo blanco #FFFFFF, look e-commerce profesional"

    # Último recurso genérico:
    return "foto de producto para e-commerce, fondo blanco, iluminación de estudio, sombras suaves, nitidez alta"


# ---------- V I S T A S  P Ú B L I C A S ----------
def home(request):
    categories = Category.objects.all().order_by("name")
    return render(request, "products/category_list.html", {"categories": categories})


def category_detail(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    subcategories = Subcategory.objects.filter(category=category).order_by("name")
    return render(
        request,
        "products/subcategory_list.html",
        {"category": category, "subcategories": subcategories},
    )


def view_options(request, subcategory_id):
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    options = ViewOption.objects.filter(subcategory=subcategory).order_by("name")
    return render(
        request,
        "products/view_options.html",
        {"subcategory": subcategory, "options": options},
    )


# ---------- E D I C I Ó N  D E  I M A G E N ----------
def _openai_edit_image(image_bytes: bytes, prompt: str, filename: str) -> bytes | None:
    """
    Llama a OpenAI por HTTP directo (sin SDK) para EDITAR una imagen
    con un prompt. Devuelve PNG bytes o None si falla.
    Modelo recomendado: gpt-image-1 (edits).
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    url = "https://api.openai.com/v1/images/edits"
    headers = {"Authorization": f"Bearer {api_key}"}

    files = {
        # La imagen subida del cliente como base
        "image": (filename, image_bytes, "image/png"),
    }
    data = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "size": "1024x1024",
        # Si tuvieses máscara, añade "mask": (....)
    }

    try:
        resp = requests.post(url, headers=headers, files=files, data=data, timeout=60)
        resp.raise_for_status()
        j = resp.json()
        b64 = j["data"][0].get("b64_json")
        if not b64:
            return None
        return base64.b64decode(b64)
    except Exception:
        return None


@login_required
def generate_photo(request, subcategory_id, view_id):
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    viewopt = get_object_or_404(ViewOption, id=view_id, subcategory=subcategory)

    result_url = None
    error_msg = None

    if request.method == "POST" and request.FILES.get("photo"):
        # Guarda la subida
        photo = request.FILES["photo"]
        original_ext = Path(photo.name).suffix.lower() or ".png"
        original_bytes = photo.read()

        base_id = f"{slugify(subcategory.category.name)}_{slugify(subcategory.name)}_{viewopt.id}"
        original_stem = Path(photo.name).stem
        safe_stem = slugify(original_stem) or "input"
        input_path = f"generated/{base_id}_{safe_stem}{original_ext}"

        try:
            saved_input = default_storage.save(input_path, ContentFile(original_bytes))
        except Exception as e:
            return render(
                request,
                "products/upload_photo.html",
                {
                    "subcategory": subcategory,
                    "viewoption": viewopt,
                    "result_url": None,
                    "error_msg": f"No se pudo guardar la imagen subida: {e}",
                },
            )

        # Llama a OpenAI edits (si hay API key)
        prompt = get_prompt_for(viewopt)
        edited_bytes = _openai_edit_image(
            image_bytes=original_bytes,
            prompt=prompt,
            filename=f"{safe_stem}.png",
        )

        # Si edición OK, guardamos resultado; si no, mostramos la subida como fallback
        try:
            if edited_bytes:
                out_name = f"generated/{base_id}_{safe_stem}_edited.png"
                saved_out = default_storage.save(out_name, ContentFile(edited_bytes))
                result_url = default_storage.url(saved_out)
            else:
                result_url = default_storage.url(saved_input)
                if not os.getenv("OPENAI_API_KEY"):
                    error_msg = "No hay clave OPENAI_API_KEY configurada; se muestra la foto original."
                else:
                    error_msg = "La edición no se pudo completar; se muestra la foto original."
        except Exception as e:
            result_url = default_storage.url(saved_input)
            error_msg = f"Error guardando el resultado; se muestra la foto original. Detalle: {e}"

    return render(
        request,
        "products/upload_photo.html",
        {
            "subcategory": subcategory,
            "viewoption": viewopt,
            "result_url": result_url,
            "error_msg": error_msg,
        },
    )
