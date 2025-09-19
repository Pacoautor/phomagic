from django.shortcuts import render

def home(request):
    return render(request, "home.html")

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.conf import settings
from .models import Category, Subcategory, MasterPrompt

import os
import base64
import requests
from io import BytesIO
from PIL import Image, ImageOps  # <- ImageOps para el margen blanco

from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------- PÁGINAS BÁSICAS ----------
def home(request):
    categories = Category.objects.all()
    return render(request, "products/home.html", {"categories": categories})

def subcategories(request, category_name):
    category = get_object_or_404(Category, name=category_name)
    subs = Subcategory.objects.filter(category=category)
    return render(request, "products/subcategories.html", {
        "category": category,
        "subcategories": subs
    })

# ---------- HELPERS OPENAI ----------
def _openai_image_edit_via_sdk(prompt: str, django_uploaded_file, size: str):
    try:
        django_uploaded_file.seek(0)
    except Exception:
        pass

    images_obj = getattr(client, "images", None)
    if images_obj is None:
        raise RuntimeError("client.images no está disponible.")

    # Algunas versiones del SDK usan .edit y otras .edits
    if hasattr(images_obj, "edit"):
        resp = images_obj.edit(
            model="gpt-image-1",
            prompt=prompt,
            image=django_uploaded_file,
            size=size,
        )
    elif hasattr(images_obj, "edits"):
        resp = images_obj.edits(
            model="gpt-image-1",
            prompt=prompt,
            image=django_uploaded_file,
            size=size,
        )
    else:
        raise AttributeError("Este SDK no soporta images.edit(s).")

    b64 = resp.data[0].b64_json
    return base64.b64decode(b64)

def _openai_image_edit_via_rest(prompt: str, django_uploaded_file, size: str):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta OPENAI_API_KEY.")

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
    data = {"model": "gpt-image-1", "prompt": prompt, "size": size, "n": 1}

    r = requests.post(url, headers=headers, files=files, data=data, timeout=300)
    r.raise_for_status()
    j = r.json()
    b64 = j["data"][0]["b64_json"]
    return base64.b64decode(b64)

def _save_and_optionally_downscale(image_bytes: bytes, base_name: str, chosen_size: str, padding_pct: float = 0.04):
    """
    Guarda 1024x1024 como principal y genera 512x512 y 256x256.
    A cada tamaño le añade un margen blanco proporcional (padding_pct).
    """
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    url_map = {}

    with Image.open(BytesIO(image_bytes)) as img_in:
        # Normaliza modo
        if img_in.mode not in ("RGB", "RGBA"):
            img_in = img_in.convert("RGBA")

        target_sizes = [("1024x1024", 1024), ("512x512", 512), ("256x256", 256)]

        for size_str, side in target_sizes:
            border_px = max(1, int(padding_pct * side))
            # Añadimos margen y redimensionamos al lienzo final cuadrado
            expanded = ImageOps.expand(img_in, border=border_px, fill="white")
            final_img = expanded.resize((side, side), resample=Image.LANCZOS)

            fn = f"{base_name}_{size_str}.png"
            p = os.path.join(settings.MEDIA_ROOT, fn)

            # Asegurar fondo blanco sólido si hay alpha
            if final_img.mode == "RGBA":
                bg = Image.new("RGB", (side, side), "white")
                bg.paste(final_img, mask=final_img.split()[-1])
                final_img = bg

            final_img.save(p, format="PNG")
            url_map[size_str] = settings.MEDIA_URL + fn

    return url_map

# ---------- GENERAR FOTO ----------
def generate_photo(request, subcategory_id):
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    prompts = MasterPrompt.objects.filter(subcategory=subcategory)

    # Previews de la foto de referencia (si existe)
    prompt_previews = {}
    for p in prompts:
        try:
            prompt_previews[p.id] = p.reference_photo.url if getattr(p, "reference_photo", None) else ""
        except Exception:
            prompt_previews[p.id] = ""

    if request.method == "POST":
        product_photo_file = request.FILES.get("product_photo")
        master_prompt_id = request.POST.get("master_prompt")

        if product_photo_file and master_prompt_id:
            mp = get_object_or_404(MasterPrompt, id=master_prompt_id)
            final_prompt = f"{mp.prompt_text}"

            try:
                # Pedimos SIEMPRE a 1024x1024 (tamaños menores se crean localmente)
                try:
                    image_bytes = _openai_image_edit_via_sdk(final_prompt, product_photo_file, "1024x1024")
                except Exception:
                    image_bytes = _openai_image_edit_via_rest(final_prompt, product_photo_file, "1024x1024")

                # Guardar original y versiones 512/256 con margen
                url_map = _save_and_optionally_downscale(
                    image_bytes,
                    f"result_{subcategory_id}",
                    "1024x1024",
                    padding_pct=0.04,  # ajusta 0.03–0.08 según te guste el margen
                )

                return render(request, "products/result.html", {
                    "subcategory": subcategory,
                    "prompt": final_prompt,
                    "urls": url_map,
                })

            except requests.HTTPError as http_err:
                return HttpResponse(f"Error HTTP de OpenAI: {http_err.response.status_code} – {http_err.response.text}")
            except Exception as e:
                return HttpResponse(f"¡Ha ocurrido un error en la API de OpenAI! Error: {e}")

    # GET: formulario
    return render(request, "products/generate_photo.html", {
        "subcategory": subcategory,
        "prompts": prompts,
        "prompt_previews": prompt_previews,
    })
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect

def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("login")
    else:
        form = UserCreationForm()
    return render(request, "signup.html", {"form": form})
