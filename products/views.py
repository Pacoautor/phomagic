# products/views.py

import os
import uuid
import base64
import logging
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect

from PIL import Image

# ===== MODELOS =====
# Ajusta si tus nombres difieren
from .models import Category, Subcategory, ViewOption, MasterPrompt

# ===== OpenAI SDK v1 =====
from openai import OpenAI

logger = logging.getLogger(__name__)


# --------------------------
# Utilidad: guardar + derivar tamaños
# --------------------------
def _save_bytes_and_downscale(img_bytes: bytes, base_name: str):
    """
    Guarda PNG 1024 y deriva 512/256 sin recorte (contain). Fondo oscuro #222.
    Devuelve dict con URLs absolutas (MEDIA_URL) para usarlas en el template.
    """
    out_dir = os.path.join(settings.MEDIA_ROOT, "results")
    os.makedirs(out_dir, exist_ok=True)

    urls = {}
    sizes = [(1024, 1024), (512, 512), (256, 256)]

    img = Image.open(BytesIO(img_bytes)).convert("RGBA")

    for w, h in sizes:
        canvas = Image.new("RGBA", (w, h), (34, 34, 34, 255))  # fondo oscuro
        thumb = img.copy()
        thumb.thumbnail((w, h), Image.LANCZOS)
        ox = (w - thumb.width) // 2
        oy = (h - thumb.height) // 2
        canvas.paste(thumb, (ox, oy), mask=thumb if thumb.mode == "RGBA" else None)

        fname = f"{base_name}_{w}x{h}.png"
        fpath = os.path.join(out_dir, fname)
        canvas.convert("RGB").save(fpath, format="PNG", optimize=True)

        # URL absoluta (MEDIA_URL termina en '/')
        urls[f"image_{w}"] = f"{settings.MEDIA_URL}results/{fname}"

    return urls


# --------------------------
# Home: categorías
# --------------------------
def home(request):
    categories = Category.objects.all().order_by("name")
    return render(request, "home.html", {"categories": categories})


# --------------------------
# Subcategorías de una categoría (por slug)
# URL de ejemplo: /c/<category_slug>/
# --------------------------
def category_detail(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    subcategories = Subcategory.objects.filter(category=category).order_by("name")
    return render(
        request,
        "products/subcategories.html",
        {"category": category, "subcategories": subcategories},
    )


# --------------------------
# Vistas disponibles para una subcategoría (por id)
# URL de ejemplo: /v/<subcategory_id>/
# --------------------------
def view_options(request, subcategory_id: int):
    subcategory = get_object_or_404(Subcategory, pk=subcategory_id)
    view_list = ViewOption.objects.filter(subcategory=subcategory).order_by("name")
    return render(
        request,
        "products/views.html",
        {
            "subcategory": subcategory,
            "view_list": view_list,
        },
    )


# --------------------------
# Generar foto (GET muestra form, POST llama a OpenAI)
# URL de ejemplo: /g/<subcategory_id>/<view_id>/
# --------------------------
def generate_photo(request, subcategory_id: int, view_id: int):
    subcategory = get_object_or_404(Subcategory, pk=subcategory_id)
    viewopt = get_object_or_404(ViewOption, pk=view_id, subcategory=subcategory)

    # Prompt maestro opcional (si lo usas en tu modelo)
    mp = (
        MasterPrompt.objects.filter(subcategory=subcategory, view=viewopt).first()
        if "MasterPrompt" in globals()
        else None
    )
    master_prompt = (mp.prompt_text or "").strip() if mp else ""

    if request.method == "GET":
        return render(
            request,
            "products/generate_photo.html",
            {
                "subcategory": subcategory,
                "viewopt": viewopt,
                "master_prompt": master_prompt,
                "master_prompt_photo": (mp.reference_photo.url if mp and mp.reference_photo else None),
            },
        )

    # ---------- POST ----------
    final_prompt = (request.POST.get("final_prompt") or master_prompt or "").strip()
    if not final_prompt:
        messages.warning(request, "Escribe un prompt para generar la imagen.")
        return redirect("generate_photo", subcategory_id=subcategory.id, view_id=viewopt.id)

    # archivo del usuario (opcional)
    uploaded = request.FILES.get("product_photo")
    img_bytes = None
    if uploaded:
        try:
            img_bytes = uploaded.read()
            logger.info(f"[gen] Archivo recibido: product_photo, {len(img_bytes)} bytes")
        except Exception as e:
            logger.exception("[gen] Error leyendo archivo subido")
            messages.error(request, f"No se pudo leer la imagen subida: {e}")
            return redirect("generate_photo", subcategory_id=subcategory.id, view_id=viewopt.id)

    # Clave OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        messages.error(request, "Falta OPENAI_API_KEY en el servidor.")
        return render(
            request,
            "products/result.html",
            {"subcategory": subcategory, "viewopt": viewopt, "image_1024": None, "image_512": None, "image_256": None},
        )

    client = OpenAI(api_key=openai_key)

    # base de nombre de archivo
    base_id = uuid.uuid4().hex
    base_name = f"{subcategory.id}_{viewopt.id}_{base_id}"

    try:
        # 1) Si hay imagen del usuario: EDIT
        if img_bytes:
            logger.info("[gen] Usando edits con gpt-image-1")
            # ✅ correcto con el SDK actual
result = client.images.edit(
    model="gpt-image-1",
    image=io.BytesIO(orig_bytes),   # un file-like de la imagen original
    prompt=final_prompt,
    size="1024x1024",
)

            b64 = result.data[0].b64_json
            out_bytes = base64.b64decode(b64)

        # 2) Si no hay imagen: GENERATE
        else:
            logger.info("[gen] Usando generate con gpt-image-1 (sin imagen base)")
            result = client.images.generate(
                model="gpt-image-1",
                prompt=final_prompt or "Foto de producto con fondo blanco, iluminación uniforme, alta calidad.",
                size="1024x1024",
            )
            b64 = result.data[0].b64_json
            out_bytes = base64.b64decode(b64)

        urls = _save_bytes_and_downscale(out_bytes, base_name)
        image_1024 = urls.get("image_1024")
        image_512 = urls.get("image_512")
        image_256 = urls.get("image_256")

        if not image_1024:
            messages.warning(request, "No se obtuvo imagen 1024x1024.")
            image_512 = image_256 = None

        return render(
            request,
            "products/result.html",
            {
                "subcategory": subcategory,
                "viewopt": viewopt,
                "prompt": final_prompt,
                "image_1024": image_1024,
                "image_512": image_512,
                "image_256": image_256,
            },
        )

    except Exception as e:
        logger.exception("[gen] Error al generar/editar imagen con OpenAI")
        messages.error(request, f"No se pudo generar la imagen. Detalle: {e}")
        return render(
            request,
            "products/result.html",
            {
                "subcategory": subcategory,
                "viewopt": viewopt,
                "prompt": final_prompt,
                "image_1024": None,
                "image_512": None,
                "image_256": None,
            },
        )
