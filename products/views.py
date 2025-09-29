# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import io
import base64
import uuid
from typing import Dict

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings

from PIL import Image

from .models import Category, Subcategory, ViewOption, MasterPrompt

# OpenAI SDK
try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# ----------------- Utilidades -----------------

def _save_bytes_and_downscale(image_bytes: bytes, base_name: str) -> Dict[str, str]:
    """
    Guarda PNG 1024 y deriva 512/256 SIN recortes, manteniendo aspecto.
    Devuelve dict con URLs relativas: {'1024x1024': url, '512x512': url, '256x256': url}
    """
    os.makedirs(os.path.join(settings.MEDIA_ROOT, "results"), exist_ok=True)

    def _fit(img: Image.Image, max_side: int) -> Image.Image:
        img = img.convert("RGBA")
        w, h = img.size
        scale = float(max_side) / max(w, h)
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        canvas = Image.new("RGBA", (max_side, max_side), (255, 255, 255, 0))
        img_resized = img.resize((new_w, new_h), Image.LANCZOS)
        off_x = (max_side - new_w) // 2
        off_y = (max_side - new_h) // 2
        canvas.paste(img_resized, (off_x, off_y), img_resized)
        return canvas.convert("RGB")

    pil_1024 = _fit(Image.open(io.BytesIO(image_bytes)), 1024)
    pil_512 = _fit(pil_1024, 512)
    pil_256 = _fit(pil_1024, 256)

    urls: Dict[str, str] = {}

    f1024 = f"{base_name}_1024.png"
    p1024 = os.path.join(settings.MEDIA_ROOT, "results", f1024)
    pil_1024.save(p1024, format="PNG", optimize=True)
    urls["1024x1024"] = settings.MEDIA_URL + "results/" + f1024

    f512 = f"{base_name}_512.png"
    p512 = os.path.join(settings.MEDIA_ROOT, "results", f512)
    pil_512.save(p512, format="PNG", optimize=True)
    urls["512x512"] = settings.MEDIA_URL + "results/" + f512

    f256 = f"{base_name}_256.png"
    p256 = os.path.join(settings.MEDIA_ROOT, "results", f256)
    pil_256.save(p256, format="PNG", optimize=True)
    urls["256x256"] = settings.MEDIA_URL + "results/" + f256

    return urls


# ----------------- Navegación -----------------

def home(request):
    categories = Category.objects.all().order_by("name")
    return render(request, "home.html", {"categories": categories})


def category_detail(request, category_slug: str):
    category = get_object_or_404(Category, slug=category_slug)
    subcategories = Subcategory.objects.filter(category=category).order_by("name")
    return render(
        request,
        "products/category_detail.html",
        {"category": category, "subcategories": subcategories},
    )


def view_options(request, subcategory_id: int):
    subcategory = get_object_or_404(Subcategory, pk=subcategory_id)
    view_list = ViewOption.objects.filter(subcategory=subcategory).order_by("name")
    return render(
        request,
        "products/views.html",
        {"subcategory": subcategory, "view_list": view_list},
    )


# ----------------- Generar por EDICIÓN (siempre) -----------------

def generate_photo(request, subcategory_id: int, view_id: int):
    """
    GET  -> formulario (sin mostrar prompt; subida obligatoria).
    POST -> EDICIÓN de la imagen subida con el prompt de MasterPrompt.
            Si el SDK no soporta edits, se devuelve error (NO hay fallback a texto).
    """
    subcategory = get_object_or_404(Subcategory, pk=subcategory_id)
    viewopt = get_object_or_404(ViewOption, pk=view_id, subcategory=subcategory)

    mp = MasterPrompt.objects.filter(subcategory=subcategory, view=viewopt).first()
    final_prompt = (mp.prompt_text or "").strip() if mp else ""
    ref_photo = mp.reference_photo if mp and mp.reference_photo else None

    if request.method == "GET":
        return render(
            request,
            "products/generate_photo.html",
            {
                "subcategory": subcategory,
                "viewopt": viewopt,
                "final_prompt": final_prompt,     # NO se muestra (sólo hidden si lo necesitas)
                "master_prompt_photo": ref_photo,
            },
        )

    # POST
    if "product_photo" not in request.FILES:
        messages.error(request, "Debes subir una imagen del producto.")
        return redirect("generate_photo", subcategory_id=subcategory.id, view_id=viewopt.id)

    if not final_prompt:
        messages.error(request, "No hay un prompt configurado para esta vista.")
        return redirect("view_options", subcategory_id=subcategory.id)

    uploaded = request.FILES["product_photo"]
    try:
        original_bytes = uploaded.read()
    except Exception:
        messages.error(request, "No se pudo leer la imagen subida.")
        return redirect("generate_photo", subcategory_id=subcategory.id, view_id=viewopt.id)

    # Guardamos original (opcional)
    upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    orig_name = f"{uuid.uuid4().hex}_{uploaded.name}".replace("\\", "/")
    orig_path = os.path.join(upload_dir, orig_name)
    with open(orig_path, "wb") as f:
        f.write(original_bytes)

    # OpenAI client
    if OpenAI is None:
        messages.error(request, "OpenAI SDK no disponible en el servidor.")
        return render(request, "products/result.html", {
            "subcategory": subcategory, "viewopt": viewopt,
            "image_1024": None, "image_512": None, "image_256": None,
        })

    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    except Exception as e:
        messages.error(request, f"No se pudo inicializar OpenAI: {e}")
        return render(request, "products/result.html", {
            "subcategory": subcategory, "viewopt": viewopt,
            "image_1024": None, "image_512": None, "image_256": None,
        })

    # EXIGIMOS edición
    if not hasattr(client.images, "edits"):
        messages.error(
            request,
            "El SDK de OpenAI instalado no soporta edición de imágenes "
            "(images.edits). Actualiza la librería 'openai' en el servidor."
        )
        return render(request, "products/result.html", {
            "subcategory": subcategory, "viewopt": viewopt,
            "image_1024": None, "image_512": None, "image_256": None,
        })

    # Edición real con foto del cliente
    gen_bytes = None
    try:
        with open(orig_path, "rb") as fimg:
            res = client.images.edits(
                model="gpt-image-1",
                image=fimg,
                prompt=final_prompt,
                size="1024x1024",
            )
        b64 = res.data[0].b64_json
        gen_bytes = base64.b64decode(b64)
    except Exception as e:
        messages.error(request, f"No se pudo editar la imagen con OpenAI: {e}")
        return render(request, "products/result.html", {
            "subcategory": subcategory, "viewopt": viewopt,
            "image_1024": None, "image_512": None, "image_256": None,
        })

    # Guardar 1024/512/256
    try:
        base_id = uuid.uuid4().hex
        urls = _save_bytes_and_downscale(gen_bytes, base_id)
        image_1024 = urls.get("1024x1024")
        image_512 = urls.get("512x512")
        image_256 = urls.get("256x256")
        messages.success(request, "Imagen editada correctamente.")
    except Exception as e:
        messages.error(request, f"No se pudo guardar/derivar las imágenes: {e}")
        image_1024 = image_512 = image_256 = None

    return render(
        request,
        "products/result.html",
        {
            "subcategory": subcategory,
            "viewopt": viewopt,
            "image_1024": image_1024,
            "image_512": image_512,
            "image_256": image_256,
        },
    )
