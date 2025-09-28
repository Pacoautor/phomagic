# products/views.py
from __future__ import annotations

import base64
import io
import os
import uuid
from typing import Dict, Optional

from django.conf import settings
from django.contrib import messages
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from PIL import Image

from .models import Category, Subcategory, ViewOption, MasterPrompt

# --- OpenAI SDK (v1.x) ---
try:
    # SDK oficial nuevo (openai>=1.0)
    from openai import OpenAI

    client: Optional[OpenAI] = OpenAI(api_key=getattr(settings, "OPENAI_API_KEY", None))
except Exception:
    client = None


# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------
def _save_bytes_and_downscale(image_bytes: bytes, base_id: str) -> Dict[str, str]:
    """
    Guarda la imagen 1024 y genera 512 y 256 SIN recortar, manteniendo aspecto.
    Devuelve dict con rutas relativas para MEDIA_URL.
    """
    rel_dir = "results"
    abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)

    paths = {
        "1024": os.path.join(abs_dir, f"{base_id}_1024.png"),
        "512": os.path.join(abs_dir, f"{base_id}_512.png"),
        "256": os.path.join(abs_dir, f"{base_id}_256.png"),
    }

    # 1024
    with open(paths["1024"], "wb") as f:
        f.write(image_bytes)

    # Redimensionados
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    for size_key, size in [("512", 512), ("256", 256)]:
        w, h = img.size
        if w == 0 or h == 0:
            continue
        scale = min(size / w, size / h)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        resized = img.resize((new_w, new_h), Image.LANCZOS)

        # Lienzo cuadrado para no recortar
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        off_x = (size - new_w) // 2
        off_y = (size - new_h) // 2
        canvas.paste(resized, (off_x, off_y))
        canvas.convert("RGB").save(paths[size_key], format="PNG", optimize=True)

    # Rutas relativas (para MEDIA_URL)
    return {
        "image_1024": os.path.join(rel_dir, f"{base_id}_1024.png").replace("\\", "/"),
        "image_512": os.path.join(rel_dir, f"{base_id}_512.png").replace("\\", "/"),
        "image_256": os.path.join(rel_dir, f"{base_id}_256.png").replace("\\", "/"),
    }


def _get_master_prompt(subcategory: Subcategory, view: ViewOption) -> Dict[str, Optional[str]]:
    """
    Devuelve prompt maestro y foto de referencia (si existen).
    """
    mp = (
        MasterPrompt.objects.filter(subcategory=subcategory, view=view)
        .order_by("id")
        .first()
    )
    if mp:
        return {
            "prompt_text": (mp.prompt_text or "").strip(),
            "reference_photo": mp.reference_photo.url if mp.reference_photo else None,
        }
    return {"prompt_text": "", "reference_photo": None}


# ---------------------------------------------------------------------
# Vistas de navegación
# ---------------------------------------------------------------------
def home(request):
    categories = Category.objects.all().order_by("id")
    return render(request, "home.html", {"categories": categories})


def subcategories(request, category_slug: str):
    category = get_object_or_404(Category, slug=category_slug)
    subcats = Subcategory.objects.filter(category=category).order_by("id")
    return render(
        request,
        "products/subcategories.html",
        {"category": category, "subcategories": subcats},
    )


def view_options(request, subcategory_id: int):
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    view_list = ViewOption.objects.filter(subcategory=subcategory).order_by("id")
    return render(
        request,
        "products/views.html",
        {
            "subcategory": subcategory,
            "view_list": view_list,  # <- tu plantilla debe usar this (antes 'views' daba conflicto)
        },
    )


# ---------------------------------------------------------------------
# Generación / edición de imagen
# URL: /g/<subcategory_id>/<view_id>/
# Templates: products/generate_photo.html (form) -> products/result.html
# ---------------------------------------------------------------------
def generate_photo(request, subcategory_id: int, view_id: int):
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    view = get_object_or_404(ViewOption, id=view_id, subcategory=subcategory)
    master = _get_master_prompt(subcategory, view)
    master_prompt = master["prompt_text"]
    master_prompt_photo = master["reference_photo"]

    if request.method == "GET":
        # Muestra el formulario
        return render(
            request,
            "products/generate_photo.html",
            {
                "subcategory": subcategory,
                "view": view,
                "master_prompt": master_prompt,
                "master_prompt_photo": master_prompt_photo,
            },
        )

    # POST: procesar
    prompt_input = (request.POST.get("prompt") or "").strip()
    uploaded_image = request.FILES.get("image")

    # Prompt final
    final_prompt = master_prompt
    if prompt_input:
        if final_prompt:
            final_prompt = f"{final_prompt}\n\n{prompt_input}"
        else:
            final_prompt = prompt_input

    # Validaciones rápidas
    if not final_prompt:
        messages.error(request, "Añade un prompt para generar la imagen.")
        return render(
            request,
            "products/generate_photo.html",
            {
                "subcategory": subcategory,
                "view": view,
                "master_prompt": master_prompt,
                "master_prompt_photo": master_prompt_photo,
            },
        )

    # Comprobar OpenAI
    if client is None or not getattr(settings, "OPENAI_API_KEY", None):
        return render(
            request,
            "products/result.html",
            {
                "subcategory": subcategory,
                "view": view,
                "final_prompt": final_prompt,
                "image_1024": None,
                "image_512": None,
                "image_256": None,
                "error_msg": "Cliente OpenAI no inicializado o falta OPENAI_API_KEY.",
            },
        )

    # Llamada a OpenAI
    base_id = uuid.uuid4().hex[:8]
    try:
        if uploaded_image:
            # EDICIÓN (con imagen base)
            orig_bytes = uploaded_image.read()
            result = client.images.edit(
                model="gpt-image-1",
                image=io.BytesIO(orig_bytes),
                prompt=final_prompt,
                size="1024x1024",
            )
        else:
            # GENERACIÓN (sin imagen base)
            result = client.images.generate(
                model="gpt-image-1",
                prompt=final_prompt,
                size="1024x1024",
            )

        # Obtener b64 y guardar 1024 + derivados
        b64 = result.data[0].b64_json
        img_bytes = base64.b64decode(b64)
        urls = _save_bytes_and_downscale(img_bytes, base_id)

        return render(
            request,
            "products/result.html",
            {
                "subcategory": subcategory,
                "view": view,
                "final_prompt": final_prompt,
                "image_1024": urls["image_1024"],
                "image_512": urls["image_512"],
                "image_256": urls["image_256"],
                "error_msg": None,
            },
        )

    except Exception as e:
        # Fallback a resultado con error
        return render(
            request,
            "products/result.html",
            {
                "subcategory": subcategory,
                "view": view,
                "final_prompt": final_prompt,
                "image_1024": None,
                "image_512": None,
                "image_256": None,
                "error_msg": f"No se pudo generar la imagen. Detalle: {e}",
            },
        )
