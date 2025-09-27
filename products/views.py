# products/views.py
import os, base64, requests
from io import BytesIO
from PIL import Image

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from .models import Category, Subcategory, ViewOption, MasterPrompt
from .forms import CustomUserCreationForm


# ----- Listado principal -----
def home(request):
    categories = Category.objects.all()
    return render(request, "products/home.html", {"categories": categories})


# products/views.py (Fragmento corregido)
# ...

def subcategories(request, category_slug): # <-- AHORA ESPERA 'category_slug'
    """
    Lista las subcategorías para la categoría dada por su slug.
    """
    # Usamos .filter(slug=category_slug) porque la URL nos da el slug, no el nombre.
    category = get_object_or_404(Category, slug=category_slug)
    
    # El resto de la lógica es la misma
    subs = Subcategory.objects.filter(category=category).order_by("name")
    return render(
        request,
        "products/subcategories.html",
        {"category": category, "subcategories": subs},
    )

# ...

def view_options(request, subcategory_id):
    """
    Lista de Vistas (frontal, lateral, etc.) para la subcategoría.
    IMPORTANT: la plantilla espera la variable 'view_list'.
    """
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    view_list = ViewOption.objects.filter(subcategory_id=subcategory_id).order_by("name")
    return render(
        request,
        "products/views.html",
        {"subcategory": subcategory, "view_list": view_list},
    )


# ----- Helpers OpenAI -----
def _openai_image_edit_via_rest(prompt: str, django_uploaded_file, size: str):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta OPENAI_API_KEY.")

    # aseguramos puntero al inicio
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


def _save_and_optionally_downscale(image_bytes: bytes, base_name: str, chosen_size: str):
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    url_map = {}

    # original (la que pedimos a OpenAI)
    main_filename = f"{base_name}_{chosen_size}.png"
    main_path = os.path.join(settings.MEDIA_ROOT, main_filename)
    with open(main_path, "wb") as f:
        f.write(image_bytes)
    url_map[chosen_size] = settings.MEDIA_URL + main_filename

    # derivados más pequeños
    for sz in ["512x512", "256x256"]:
        w, h = map(int, sz.split("x"))
        with Image.open(BytesIO(image_bytes)) as img:
            resized = img.resize((w, h), resample=Image.LANCZOS)
            fn = f"{base_name}_{sz}.png"
            p = os.path.join(settings.MEDIA_ROOT, fn)
            resized.save(p)
            url_map[sz] = settings.MEDIA_URL + fn

    return url_map


# ----- Generación -----
def generate_photo(request, subcategory_id, view_id):
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    viewopt = get_object_or_404(ViewOption, id=view_id, subcategory_id=subcategory_id)
    
    # Prompts preferentemente filtrados por vista; si no hay, por subcategoría sin vista
    prompts = MasterPrompt.objects.filter(subcategory_id=subcategory_id, view_id=view_id)
    if not prompts.exists():
        prompts = MasterPrompt.objects.filter(subcategory_id=subcategory_id, view__isnull=True)

    # Miniaturas de referencia (si existen)
    prompt_previews = {}
    for p in prompts:
        try:
            prompt_previews[p.id] = p.reference_photo.url if getattr(p, "reference_photo", None) else ""
        except Exception:
            prompt_previews[p.id] = ""

    # Lógica de generación y renderizado
    if request.method == "POST":
        product_photo_file = request.FILES.get("product_photo")
        master_prompt_id = request.POST.get("master_prompt")
        
        urls = {}
        error_msg = None
        final_prompt = ""

        if product_photo_file and master_prompt_id:
            try:
                mp = get_object_or_404(MasterPrompt, id=master_prompt_id)
                final_prompt = f"{mp.prompt_text}"
                
                # Generación de la imagen
                image_bytes = _openai_image_edit_via_rest(final_prompt, product_photo_file, "1024x1024")
                
                # Guardado y escalado
                urls = _save_and_optionally_downscale(
                    image_bytes, f"result_{subcategory_id}_{view_id}", "1024x1024"
                )

            except requests.HTTPError as http_err:
                error_msg = f"Error HTTP de OpenAI: {http_err.response.status_code} – {http_err.response.text}"
            except Exception as e:
                error_msg = f"¡Ha ocurrido un error en la API de OpenAI! Error: {e}"

        # Lógica de verificación y renderizado (integrada de la función `generate_result`)
        
        # Alias para el template
        safe_urls = {
            "image_1024": urls.get("1024x1024"),
            "image_512": urls.get("512x512"),
            "image_256": urls.get("256x256"),
        }

        # Si hubo un error en la generación y no tenemos URLs, ponemos un mensaje genérico.
        if not safe_urls["image_1024"] and not error_msg:
            error_msg = (
                "No se generó ninguna imagen. Si estás usando OpenAI, "
                "revisa el saldo/limite de facturación y los logs del servicio."
            )
        
        # Si tienes error_msg, sobrescribe las URLs a None para evitar mostrar URLs inválidas.
        if error_msg:
            safe_urls = {
                "image_1024": None,
                "image_512": None,
                "image_256": None,
            }

        return render(
            request,
            "products/result.html",
            {
                "subcategory": subcategory,
                "viewopt": viewopt,
                "prompt": final_prompt,
                "image_1024": safe_urls["image_1024"],
                "image_512": safe_urls["image_512"],
                "image_256": safe_urls["image_256"],
                "error_msg": error_msg,
            },
        )
    
    # Renderizado del formulario inicial
    return render(
        request,
        "products/generate_photo.html",
        {"subcategory": subcategory, "viewopt": viewopt, "prompts": prompts, "prompt_previews": prompt_previews},
    )


# ----- Registro (por si lo usas aquí) -----
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