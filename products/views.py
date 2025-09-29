import os
import base64
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.utils.text import slugify
from PIL import Image
from openai import OpenAI
from .models import Category, GeneratedImage

# Inicializar cliente OpenAI
client = OpenAI()


def home(request):
    categories = Category.objects.all()
    return render(request, "home.html", {"categories": categories})


def category_detail(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    return render(
        request,
        "products/category_detail.html",
        {"category": category, "view_list": True},
    )


@login_required
def generate_photo(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == "POST" and request.FILES.get("photo"):
        uploaded_file = request.FILES["photo"]

        # Guardar foto original del cliente
        original_filename = slugify(os.path.splitext(uploaded_file.name)[0])
        base_id = f"{category.slug}_{original_filename}"
        media_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
        os.makedirs(media_dir, exist_ok=True)
        original_path = os.path.join(media_dir, uploaded_file.name)
        with default_storage.open(original_path, "wb+") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        # Construir el prompt interno (no visible al usuario)
        final_prompt = f"Aplica el estilo de la categoría {category.name} a la imagen proporcionada."

        # Directorio para resultados
        results_dir = os.path.join(settings.MEDIA_ROOT, "results")
        os.makedirs(results_dir, exist_ok=True)
        results_url = os.path.join(settings.MEDIA_URL, "results")

        try:
            # Llamada a OpenAI: edición con la foto subida
            with open(original_path, "rb") as img_f:
                result = client.images.edits(
                    model="gpt-image-1",
                    image=img_f,
                    prompt=final_prompt,
                    size="1024x1024",
                    n=1,
                )

            # Decodificar respuesta base64
            b64 = result.data[0].b64_json
            img_bytes = base64.b64decode(b64)
            im = Image.open(io.BytesIO(img_bytes)).convert("RGBA")

            # Guardar versión 1024
            save_path_1024 = os.path.join(results_dir, f"{base_id}_1024.png")
            im.save(save_path_1024, "PNG", optimize=True)

            # Derivar 512 y 256
            for sz, out_name in [(512, f"{base_id}_512.png"), (256, f"{base_id}_256.png")]:
                im_copy = im.copy()
                bg = Image.new("RGBA", (sz, sz), (255, 255, 255, 0))
                im_copy.thumbnail((sz, sz), Image.LANCZOS)
                x = (sz - im_copy.width) // 2
                y = (sz - im_copy.height) // 2
                bg.paste(im_copy, (x, y), im_copy)
                bg.save(os.path.join(results_dir, out_name), "PNG", optimize=True)

            # Construir URLs para el template
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

            # Guardar en la base de datos
            GeneratedImage.objects.create(
                category=category,
                user=request.user,
                prompt=final_prompt,
                image_1024=f"results/{base_id}_1024.png",
                image_512=f"results/{base_id}_512.png",
                image_256=f"results/{base_id}_256.png",
            )

        except Exception as e:
            urls = {"1024x1024": None, "512x512": None, "256x256": None}
            error_msg = f"No se pudo generar la imagen. Detalle: {e}"

        return render(
            request,
            "generate_photo.html",
            {"category": category, "urls": urls, "error": error_msg},
        )

    return render(request, "upload_photo.html", {"category": category})
