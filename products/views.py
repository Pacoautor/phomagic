import os
import io
import base64
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.utils.text import slugify
from PIL import Image
from openai import OpenAI

from .models import Category, Subcategory, ViewOption

# Cliente OpenAI (requiere OPENAI_API_KEY en el entorno)
client = OpenAI()


def home(request):
    """Portada con todas las categorías."""
    categories = Category.objects.all()
    return render(request, "home.html", {"categories": categories})


def category_detail(request, category_slug):
    """Detalle de una categoría (p. ej. /c/moda/)."""
    category = get_object_or_404(Category, slug=category_slug)
    # Si tus subcategorías se muestran en esta página, puedes cargarlas así:
    subcats = Subcategory.objects.filter(category=category).order_by("name")
    return render(
        request,
        "products/category_detail.html",
        {"category": category, "subcategories": subcats},
    )


def view_options(request, subcategory_id):
    """
    Lista de vistas disponibles para una subcategoría (p. ej. /v/6/).
    Renderiza products/views.html con:
      - subcategory
      - view_list  (IMPORTANTE: la plantilla debe usar 'view_list')
    """
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    view_list = ViewOption.objects.filter(subcategory=subcategory).order_by("name")
    return render(
        request,
        "products/views.html",
        {"subcategory": subcategory, "view_list": view_list},
    )


@login_required
def generate_photo(request, subcategory_id, view_id):
    """
    Sube la foto del cliente y aplica el prompt interno + la vista elegida.
    Rutas típicas: /g/<subcategory_id>/<view_id>/
      - GET  -> muestra formulario (solo input de archivo + botón)
      - POST -> procesa y muestra resultado (1024/512/256)
    """
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    viewopt = get_object_or_404(ViewOption, id=view_id, subcategory=subcategory)
    category = subcategory.category

    if request.method == "POST" and request.FILES.get("photo"):
        # 1) Guardar imagen original del cliente
        uploaded_file = request.FILES["photo"]
        original_stem = slugify(os.path.splitext(uploaded_file.name)[0]) or "foto"
        base_id = f"{category.slug}_{subcategory.slug}_{viewopt.id}_{original_stem}"

        upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        original_fs_path = os.path.join(upload_dir, uploaded_file.name)

        with default_storage.open(original_fs_path, "wb+") as out:
            for chunk in uploaded_file.chunks():
                out.write(chunk)

        # 2) Prompt interno (NO se muestra en plantillas)
        #    Puedes enriquecerlo con campos de la vista si los tienes (p. ej. viewopt.prompt_suffix)
        final_prompt = (
            f"Aplica el estilo '{viewopt.name}' propio de la subcategoría "
            f"'{subcategory.name}' dentro de la categoría '{category.name}' "
            "a la imagen proporcionada. Mejora iluminación, limpieza del producto, "
            "consistencia y presentación, manteniendo el encuadre natural siempre que sea posible."
        )

        # 3) Carpeta de salida
        results_dir = os.path.join(settings.MEDIA_ROOT, "results")
        os.makedirs(results_dir, exist_ok=True)

        try:
            # 4) Edición sobre la foto del cliente con el SDK nuevo
            with open(original_fs_path, "rb") as img_f:
                result = client.images.edits(
                    model="gpt-image-1",
                    image=img_f,           # imagen base (cliente)
                    prompt=final_prompt,   # prompt interno (oculto)
                    size="1024x1024",
                    n=1,
                )

            # 5) Decodificar resultado
            b64 = result.data[0].b64_json
            img_bytes = base64.b64decode(b64)
            im = Image.open(io.BytesIO(img_bytes)).convert("RGBA")

            # 6) Guardar 1024 y derivar 512/256 centradas
            path_1024 = os.path.join(results_dir, f"{base_id}_1024.png")
            im.save(path_1024, "PNG", optimize=True)

            def _fit_and_save(src_im: Image.Image, size: int, out_path: str):
                canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
                tmp = src_im.copy()
                tmp.thumbnail((size, size), Image.LANCZOS)
                x = (size - tmp.width) // 2
                y = (size - tmp.height) // 2
                canvas.paste(tmp, (x, y), tmp)
                canvas.save(out_path, "PNG", optimize=True)

            path_512 = os.path.join(results_dir, f"{base_id}_512.png")
            path_256 = os.path.join(results_dir, f"{base_id}_256.png")
            _fit_and_save(im, 512, path_512)
            _fit_and_save(im, 256, path_256)

            # 7) URLs públicas para la plantilla
            results_url = os.path.join(settings.MEDIA_URL, "results")
            urls = {
                "1024x1024": request.build_absolute_uri(
                    os.path.join(results_url, f"{base_id}_1024.png")
                ),
                "512x512": request.build_absolute_uri(
                    os.path.join(results_url, f"{base_id}_512.png")
                ),
                "256x256": request.build_absolute_uri(
                    os.path.join(results_url, f"{base_id}_256.png")
                ),
            }
            error_msg = None

        except Exception as e:
            # Si el servidor no tiene el SDK nuevo, lo avisamos sin romper
            urls = {"1024x1024": None, "512x512": None, "256x256": None}
            error_msg = (
                "El SDK de OpenAI instalado no soporta edición de imágenes "
                "(images.edits). Actualiza la librería 'openai' en el servidor. "
                f"Detalle: {e}"
            )

        return render(
            request,
            "products/generate_photo.html",  # muestra resultado
            {
                "category": category,
                "subcategory": subcategory,
                "viewopt": viewopt,
                "urls": urls,
                "error": error_msg,
            },
        )

    # GET: formulario simple (solo input de archivo). No mostramos ningún prompt.
    return render(
        request,
        "products/upload_photo.html",
        {"category": category, "subcategory": subcategory, "viewopt": viewopt},
    )
