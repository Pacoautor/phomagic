# products/views.py
import base64
import io
import os
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, render
from django.core.files.base import ContentFile

from PIL import Image

# MODELOS
from .models import Category, Subcategory, ViewOption, MasterPrompt

# OpenAI (SDK v1.x)
try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# ---------- helpers ----------
def _openai_client():
    """Devuelve cliente OpenAI o None si no hay SDK/KEY."""
    api_key = getattr(settings, "OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    if not api_key or OpenAI is None:
        return None
    try:
        return OpenAI(api_key=api_key)
    except Exception:
        return None


def _save_png_from_b64(png_b64: str, base_name: str) -> str:
    """
    Guarda un PNG (base64 sin encabezado) en MEDIA/results y devuelve su URL.
    Crea además variantes 1024/512/256 (manteniendo aspecto).
    """
    media_root = Path(settings.MEDIA_ROOT)
    out_dir = media_root / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    # archivo principal
    main_name = f"{base_name}.png"
    main_path = out_dir / main_name

    raw = base64.b64decode(png_b64)
    main_path.write_bytes(raw)

    # generar escalas
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        for size in (1024, 512, 256):
            canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
            im = img.copy()
            im.thumbnail((size, size), Image.LANCZOS)
            x = (size - im.width) // 2
            y = (size - im.height) // 2
            canvas.paste(im, (x, y), im if im.mode == "RGBA" else None)
            canvas.convert("RGB").save(out_dir / f"{base_name}_{size}.png", format="PNG", optimize=True)
    except Exception:
        # si falla el procesamiento, dejamos solo el original
        pass

    return settings.MEDIA_URL + "results/" + main_name


# ---------- vistas ----------
def home(request):
    categories = Category.objects.all().order_by("name")
    return render(request, "home.html", {"categories": categories})


def category_detail(request, category_slug):
    """
    Muestra las subcategorías de una categoría.
    URL: /c/<slug>/
    """
    category = get_object_or_404(Category, slug=category_slug)
    subcategories = Subcategory.objects.filter(category=category).order_by("name")
    return render(
        request,
        "products/category_detail.html",  # usa tu template existente; si no, crea uno básico
        {"category": category, "subcategories": subcategories},
    )


def view_options(request, subcategory_id: int):
    """
    Lista las vistas (ViewOption) disponibles para una subcategoría.
    URL: /v/<subcategory_id>/
    """
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    view_list = ViewOption.objects.filter(subcategory=subcategory).order_by("name")

    # MasterPrompt ilustrativo (por si lo muestras en la página)
    mp = MasterPrompt.objects.filter(subcategory=subcategory).first()
    return render(
        request,
        "products/views.html",
        {"subcategory": subcategory, "view_list": view_list, "master_prompt": mp},
    )


def generate_photo(request, subcategory_id: int, view_id: int):
    """
    Formulario + generación de imagen.
    GET: muestra el form (prompt + file)
    POST: llama a OpenAI y guarda/retorna la imagen
    """
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    viewopt = get_object_or_404(ViewOption, id=view_id, subcategory=subcategory)

    # prompt base desde MasterPrompt (opcional)
    mp = MasterPrompt.objects.filter(subcategory=subcategory, view_id=view_id).first()
    base_prompt = (mp.prompt_text or "").strip() if mp else ""

    client = _openai_client()
    generated_image_url = None  # para mostrar en template si se genera

    if request.method == "POST":
        user_prompt = (request.POST.get("final_prompt") or "").strip()
        prompt = user_prompt or base_prompt or f"Product photo for {subcategory.name} - {viewopt.name}"

        # fichero opcional del usuario
        f = request.FILES.get("product_photo")

        # --- Llamada a OpenAI ---
        if client is None:
            messages.error(request, "OpenAI no está configurado en el servidor (revisa API key/SDK).")
        else:
            try:
                # SDK v1.x – generación simple (prompt -> imagen)
                # Si más adelante quieres activar image-to-image (edits), te paso el bloque después.
                resp = client.images.generate(
                    model="gpt-image-1",
                    prompt=prompt if not f else f"{prompt}. Improve the look of the uploaded product photo.",
                    size="1024x1024",
                )
                b64_data = resp.data[0].b64_json
                file_id = uuid.uuid4().hex
                generated_image_url = _save_png_from_b64(b64_data, f"gen_{file_id}")
                messages.success(request, "Imagen generada correctamente.")
            except Exception as e:
                messages.error(request, f"No se pudo generar la imagen. Detalle: {e}")

        # Render del resultado (muestra la imagen si existe)
        return render(
            request,
            "products/generate_photo.html",
            {
                "subcategory": subcategory,
                "viewopt": viewopt,
                "final_prompt": user_prompt or base_prompt,
                "master_prompt_photo": mp.reference_photo if mp and mp.reference_photo else None,
                "generated_image_url": generated_image_url,
            },
        )

    # GET
    return render(
        request,
        "products/generate_photo.html",
        {
            "subcategory": subcategory,
            "viewopt": viewopt,
            "final_prompt": base_prompt,
            "master_prompt_photo": mp.reference_photo if mp and mp.reference_photo else None,
            "generated_image_url": None,
        },
    )

