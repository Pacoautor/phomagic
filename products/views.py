import os
import io
import uuid
import base64

import requests
from PIL import Image
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.core.files.storage import default_storage
from django.shortcuts import render, get_object_or_404, redirect

from .models import Category, Subcategory, ViewOption, MasterPrompt
from .forms import CustomUserCreationForm


# ---------------------------
# Helpers
# ---------------------------

def _save_bytes_and_downscale(image_bytes: bytes, base_name: str) -> dict:
    """
    Guarda una imagen base 1024x1024 y deriva 512/256 **SIN recortes** (se rellena con fondo blanco).
    Devuelve un dict con URLs relativas servibles por MEDIA_URL (o default_storage si aplica).
    """
    out_dir = os.path.join(settings.MEDIA_ROOT, "results")
    os.makedirs(out_dir, exist_ok=True)

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    urls = {}

    for w, h in [(1024, 1024), (512, 512), (256, 256)]:
        # Lienzo blanco y centrado manteniendo aspecto (sin recortar)
        bg = Image.new("RGBA", (w, h), (255, 255, 255, 255))
        im = img.copy()
        im.thumbnail((w, h), Image.LANCZOS)
        x = (w - im.width) // 2
        y = (h - im.height) // 2
        bg.paste(im, (x, y), im)

        fname = f"{base_name}_{w}x{h}.png"
        fpath = os.path.join(out_dir, fname)
        bg.convert("RGB").save(fpath, "PNG", optimize=True)

        rel = os.path.join("results", fname).replace("\\", "/")
        # Si usas almacenamiento remoto, default_storage.url genera URL pública
        try:
            urls[f"{w}x{h}"] = default_storage.url(rel)
        except Exception:
            urls[f"{w}x{h}"] = settings.MEDIA_URL + rel

    return urls


def _openai_image_edit_via_rest(prompt: str, django_uploaded_file, size: str = "1024x1024") -> bytes:
    """
    Llama a OpenAI /v1/images/edits usando model=gpt-image-1 con la foto subida.
    Devuelve los bytes de la imagen generada (PNG).
    """
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key or api_key.strip() in ("", "sk-test", "CLAVE_DE_PRUEBA_FALLIDA"):
        raise RuntimeError(
            "OPENAI_API_KEY no está configurada o no es válida en el entorno (Render)."
        )

    # Asegura el puntero al inicio del UploadedFile
    try:
        django_uploaded_file.seek(0)
    except Exception:
        pass

    url = "https://api.openai.com/v1/images/edits"
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {
        "image": (
            django_uploaded_file.name,
            django_uploaded_file,
            getattr(django_uploaded_file, "content_type", None) or "application/octet-stream",
        ),
    }
    data = {
        "model": "gpt-image-1",
        "prompt": prompt or "Mejora la foto del producto con fondo blanco limpio.",
        "size": size,
        "n": 1,
    }

    resp = requests.post(url, headers=headers, files=files, data=data, timeout=300)
    resp.raise_for_status()
    b64 = resp.json()["data"][0]["b64_json"]
    return base64.b64decode(b64)


# ---------------------------
# Vistas públicas
# ---------------------------

def home(request):
    categories = Category.objects.all()
    return render(request, "products/home.html", {"categories": categories})


def subcategories(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    subs = Subcategory.objects.filter(category=category).order_by("name")
    return render(
        request,
        "products/subcategories.html",
        {"category": category, "subcategories": subs},
    )


def view_options(request, subcategory_id):
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    view_list = ViewOption.objects.filter(subcategory_id=subcategory_id).order_by("name")
    return render(
        request,
        "products/views.html",
        {"subcategory": subcategory, "view_list": view_list},
    )


# ---------------------------
# Generación principal
# ---------------------------

def generate_photo(request, subcategory_id, view_id):
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    viewopt = get_object_or_404(ViewOption, id=view_id, subcategory_id=subcategory_id)

    # Prompt preferente para (subcat, vista); si no hay, cae al de subcat sin vista
    mp = (
        MasterPrompt.objects.filter(subcategory_id=subcategory_id, view_id=view_id).first()
        or MasterPrompt.objects.filter(subcategory_id=subcategory_id, view__isnull=True).first()
    )
    final_prompt = (mp.prompt_text or "").strip() if mp else ""
    prompt_previews = [final_prompt] if final_prompt else []

    if request.method == "GET":
        return render(
            request,
            "products/generate_photo.html",
            {
                "subcategory": subcategory,
                "viewopt": viewopt,
                "prompts": [final_prompt] if final_prompt else [],
                "prompt_previews": prompt_previews,
            },
        )

    # POST: imagen del usuario
    product_photo = request.FILES.get("product_photo")
    if not product_photo:
        messages.error(request, "Debes subir una imagen de producto.")
        return render(
            request,
            "products/generate_photo.html",
            {
                "subcategory": subcategory,
                "viewopt": viewopt,
                "prompts": [final_prompt] if final_prompt else [],
                "prompt_previews": prompt_previews,
            },
        )

    # Guarda ORIGINAL (opcional, por trazabilidad)
    upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    base_id = f"{subcategory_id}_{view_id}_{uuid.uuid4().hex[:8]}"
    orig_name = f"orig_{base_id}.png"
    orig_path = os.path.join(upload_dir, orig_name)
    with open(orig_path, "wb") as f:
        for chunk in product_photo.chunks():
            f.write(chunk)

    urls, error_msg = {}, None

    try:
        gen_bytes = _openai_image_edit_via_rest(final_prompt, open(orig_path, "rb"), "1024x1024")
        urls = _save_bytes_and_downscale(gen_bytes, f"result_{base_id}")

    except requests.HTTPError as http_err:
        status = http_err.response.status_code
        details = http_err.response.text[:200]
        if status == 401:
            error_msg = "OpenAI 401: clave API inválida en Render."
        elif status == 400 and "billing" in details.lower():
            error_msg = "OpenAI 400: límite/saldo de facturación alcanzado."
        else:
            error_msg = f"Error HTTP de OpenAI: {status}. Detalles: {details}."

    except RuntimeError as e:
        error_msg = f"Configuración: {e}"

    except Exception as e:
        error_msg = f"Error inesperado al generar: {e}"

    # Si hubo error duro, NO mostramos URLs
    if error_msg and not urls:
        image_1024 = image_512 = image_256 = None
    else:
        image_1024 = urls.get("1024x1024")
        image_512 = urls.get("512x512")
        image_256 = urls.get("256x256")

    if error_msg and (image_1024 or image_512 or image_256):
        messages.warning(request, error_msg)
    elif error_msg:
        messages.error(
            request,
            "No se generó ninguna imagen. Revisa clave/saldo de OpenAI o vuelve a intentarlo.",
        )

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


# ---------------------------
# Registro
# ---------------------------

def signup(request):
    """Nombre de vista 'signup' para que coincida con tu urls.py."""
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cuenta creada con éxito. Ahora puedes iniciar sesión.")
            return redirect("login")
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/signup.html", {"form": form})
