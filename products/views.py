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

from .models import Category  # OJO: solo Category; no hay GeneratedImage

# Cliente OpenAI (usa OPENAI_API_KEY del entorno)
client = OpenAI()


def home(request):
    """Portada con categorías."""
    categories = Category.objects.all()
    return render(request, "home.html", {"categories": categories})


def category_detail(request, category_slug):
    """Detalle de categoría (p.e. /c/moda/)."""
    category = get_object_or_404(Category, slug=category_slug)
    return render(
        request,
        "products/category_detail.html",
        {"category": category},
    )


@login_required
def generate_photo(request, category_id):
    """
    Sube la foto del cliente y aplica el prompt interno a esa foto (edición).
    Rutas típicas:
      - GET  /g/<category_id>/   -> muestra formulario de subida
      - POST /g/<category_id>/   -> procesa imagen y enseña resultados
    """
    category = get_object_or_404(Category, id=category_id)

    if request.method == "POST" and request.FILES.get("photo"):
        # 1) Guardar la imagen original
        uploaded_file = request.FILES["photo"]
        original_stem = slugify(os.path.splitext(uploaded_file.name)[0]) or "foto"
        base_id = f"{category.slug}_{original_stem}"

        upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        original_fs_path = os.path.join(upload_dir, uploaded_file.name)

        with default_storage.open(original_fs_path, "wb+") as out:
            for chunk in uploaded_file.chunks():
                out.write(chunk)

        # 2) Prompt interno (NO se muestra en ninguna plantilla)
        final_prompt = f"Aplica el estilo y la presentación de la categoría {category.name} a la imagen proporcionada. Mejora iluminación, limpieza y consistencia del producto sin alterar el fondo original si es posible."

        # 3) Carpeta de salida
        results_dir = os.path.join(settings.MEDIA_ROOT, "results")
        os.makedirs(results_dir, exist_ok=True)

        try:
            # 4) Llamada a OpenAI: edición con imagen subida
            with open(original_fs_path, "rb") as img_f:
                result = client.images.edits(
                    model="gpt-image-1",
                    image=img_f,            # imagen base del cliente
                    prompt=final_prompt,    # prompt oculto
                    size="1024x1024",
                    n=1,
                )

            # 5) Decodificar y abrir imagen resultante
            b64 = result.data[0].b64_json
            img_bytes = base64.b64decode(b64)
            im = Image.open(io.BytesIO(img_bytes)).convert("RGBA")

            # 6) Guardar 1024 y derivar 512/256 manteniendo aspecto centrado
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

            # 7) Construir URLs absolutas para el template
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
            # En entornos con SDK viejo aparecería algo como:
            # "'Images' object has no attribute 'edits'"
            urls = {"1024x1024": None, "512x512": None, "256x256": None}
            error_msg = (
                "El SDK de OpenAI instalado no soporta edición de imágenes "
                "(images.edits). Actualiza la librería 'openai' en el servidor. "
                f"Detalle: {e}"
            )

        return render(
            request,
            "products/generate_photo.html",  # plantilla de resultado
            {"category": category, "urls": urls, "error": error_msg},
        )

    # GET: formulario de subida (sin prompt visible)
    return render(
        request,
        "products/upload_photo.html",
        {"category": category},
    )
