
import io
from PIL import Image, ImageOps

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from .models import Category, Subcategory, ViewOption, GeneratedImage


# ------------------------
# Utilidad: añadir borde blanco de 50px
# ------------------------
def add_white_border_50(image: Image.Image) -> Image.Image:
    """
    Devuelve una nueva imagen con 50px de borde blanco alrededor.
    Mantiene el modo de color apropiado.
    """
    # Asegurar modo RGB (para fondo blanco consistente)
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")

    # expand con borde de 50 px, fill blanco
    bordered = ImageOps.expand(image, border=50, fill="white")
    return bordered


# ------------------------
# Páginas básicas (ajusta templates existentes)
# ------------------------
def home(request):
    categories = Category.objects.all()
    # Ajusta este template según tu proyecto (antes ya lo tenías)
    return render(request, "home.html", {"categories": categories})


def category_detail(request, category_slug: str):
    category = get_object_or_404(Category, slug=category_slug)
    subcategories = category.subcategories.all()
    return render(
        request,
        "products/category_detail.html",
        {"category": category, "subcategories": subcategories},
    )


def view_options(request, subcategory_id: int):
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    options = subcategory.view_options.all()
    return render(
        request,
        "products/view_options.html",
        {"subcategory": subcategory, "options": options},
    )


# ------------------------
# Generar imagen SIEMPRE a partir de foto del cliente + prompt interno
# ------------------------
@login_required
def generate_photo(request, subcategory_id: int, viewoption_id: int):
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    viewoption = get_object_or_404(ViewOption, id=viewoption_id, subcategory=subcategory)

    if request.method == "GET":
        return render(
            request,
            "products/upload_photo.html",
            {"subcategory": subcategory, "viewoption": viewoption},
        )

    if request.method != "POST":
        raise Http404()

    # 1) Validación básica
    upload = request.FILES.get("photo")
    if not upload:
        return render(
            request,
            "products/upload_photo.html",
            {
                "subcategory": subcategory,
                "viewoption": viewoption,
                "error": "Por favor sube una imagen.",
            },
            status=400,
        )

    # 2) Guardar entrada
    gen = GeneratedImage(subcategory=subcategory, viewoption=viewoption)
    gen.input_image.save(upload.name, upload, save=True)

    # 3) Abrimos la imagen de entrada con PIL
    with default_storage.open(gen.input_image.name, "rb") as f:
        img = Image.open(f)
        img.load()

    # 4) (Opcional) APLICAR IA con prompt interno (NO visible al cliente)
    #    Si tienes integrada tu llamada al modelo de IA (edición guiada por prompt),
    #    sustituye el bloque a continuación. Si no, usaremos la imagen del cliente.
    #
    #    EJEMPLO DE LUGAR DONDE INTEGRAR TU IA:
    #    prompt_privado = viewoption.prompt or ""
    #    result_img = tu_funcion_de_IA(img, prompt_privado)
    #
    #    Para no romper nada, por ahora tomamos la imagen del cliente como base:
    result_img = img

    # 5) AÑADIR BORDE BLANCO DE 50 PX
    result_bordered = add_white_border_50(result_img)

    # 6) Guardar salida en storage (JPEG sRGB)
    out_buffer = io.BytesIO()
    save_params = {"format": "JPEG", "quality": 90}
    # Si viene con transparencia, convertir a RGB (blanco de fondo)
    if result_bordered.mode == "RGBA":
        bg = Image.new("RGB", result_bordered.size, "white")
        bg.paste(result_bordered, mask=result_bordered.split()[-1])
        bg.save(out_buffer, **save_params)
    else:
        if result_bordered.mode != "RGB":
            result_bordered = result_bordered.convert("RGB")
        result_bordered.save(out_buffer, **save_params)

    out_content = ContentFile(out_buffer.getvalue())
    out_name = f"generated_{subcategory.slug}_{viewoption.id}.jpg" if hasattr(subcategory, "slug") else f"generated_{subcategory.id}_{viewoption.id}.jpg"
    gen.output_image.save(out_name, out_content, save=True)

    # 7) Mostrar resultado
    # La plantilla mostrará result_url si existe
    result_url = default_storage.url(gen.output_image.name)
    return render(
        request,
        "products/upload_photo.html",
        {
            "subcategory": subcategory,
            "viewoption": viewoption,
            "result_url": result_url,
        },
    )
