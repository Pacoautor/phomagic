# products/views.py
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.conf import settings
from .models import Category, Subcategory, ViewOption, MasterPrompt

import os, base64, requests
from io import BytesIO
from PIL import Image, ImageOps

from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

def view_options(request, subcategory_id):
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    views = ViewOption.objects.filter(subcategory=subcategory).order_by("name")
    return render(request, "products/views.html", {
        "subcategory": subcategory,
        "views": views
    })

# ---- Helpers OpenAI (los mismos que ya usas) ----
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
    data = {"model": "gpt-image-1", "prompt": prompt, "size": "1024x1024", "n": 1}
    r = requests.post(url, headers=headers, files=files, data=data, timeout=300)
    r.raise_for_status()
    j = r.json()
    b64 = j["data"][0]["b64_json"]
    return base64.b64decode(b64)

def _save_and_optionally_downscale(image_bytes: bytes, base_name: str, chosen_size: str):
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    url_map = {}
    main_filename = f"{base_name}_{chosen_size}.png"
    main_path = os.path.join(settings.MEDIA_ROOT, main_filename)
    with open(main_path, "wb") as f:
        f.write(image_bytes)
    url_map[chosen_size] = settings.MEDIA_URL + main_filename
    downsizes = ["512x512", "256x256"]
    with Image.open(BytesIO(image_bytes)) as img:
        for sz in downsizes:
            w, h = map(int, sz.split("x"))
            resized = img.resize((w, h), resample=Image.LANCZOS)
            fn = f"{base_name}_{sz}.png"
            p = os.path.join(settings.MEDIA_ROOT, fn)
            resized.save(p)
            url_map[sz] = settings.MEDIA_URL + fn
    return url_map

def generate_photo(request, subcategory_id, view_id):
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    viewopt = get_object_or_404(ViewOption, id=view_id, subcategory=subcategory)

    # Prompts filtrados por Vista (si no hay, caerá a los que no tienen vista)
    prompts = MasterPrompt.objects.filter(subcategory=subcategory, view=viewopt)
    if not prompts.exists():
        prompts = MasterPrompt.objects.filter(subcategory=subcategory, view__isnull=True)

    # Previews de referencia
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
                image_bytes = _openai_image_edit_via_rest(final_prompt, product_photo_file, "1024x1024")
                url_map = _save_and_optionally_downscale(
                    image_bytes, f"result_{subcategory_id}_{view_id}", "1024x1024"
                )
                return render(request, "products/result.html", {
                    "subcategory": subcategory,
                    "viewopt": viewopt,
                    "prompt": final_prompt,
                    "urls": url_map,
                })
            except requests.HTTPError as http_err:
                return HttpResponse(f"Error HTTP de OpenAI: {http_err.response.status_code} – {http_err.response.text}")
            except Exception as e:
                return HttpResponse(f"¡Ha ocurrido un error en la API de OpenAI! Error: {e}")

    return render(request, "products/generate_photo.html", {
        "subcategory": subcategory,
        "viewopt": viewopt,
        "prompts": prompts,
        "prompt_previews": prompt_previews,
    })
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate
from .forms import CustomUserCreationForm

def signup_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cuenta creada con éxito. Ahora puedes iniciar sesión.")
            return redirect("login")
    else:
        form = CustomUserCreationForm()

    return render(request, "registration/signup.html", {"form": form})
   
       
