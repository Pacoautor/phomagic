# products/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import Category, Subcategory, ViewOption, GeneratedImage
import os
import re
from uuid import uuid4

@login_required
def generate_photo(request, subcategory_id, viewoption_id):
    """
    Sube la foto del cliente y genera una imagen aplicando el prompt
    definido por la vista elegida. Nunca muestra el prompt al usuario.
    """
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    viewopt = get_object_or_404(ViewOption, id=viewoption_id, subcategory=subcategory)
    category = subcategory.category  # padre

    if request.method == "POST":
        upload = request.FILES.get("photo")
        if not upload:
            messages.error(request, "Debes subir una imagen.")
            return redirect("generate_photo", subcategory_id=subcategory.id, viewoption_id=viewopt.id)

        # Guardar temporalmente la imagen subida
        # (Render usa almacenamiento de archivos; MEDIA_ROOT ya está configurado)
        original_name = upload.name or "upload.jpg"
        original_stem, ext = os.path.splitext(original_name)

        # Sanitizar nombre base para evitar caracteres raros en el path
        def slugify_light(s):
            s = re.sub(r"\s+", "-", s.strip().lower())
            s = re.sub(r"[^a-z0-9\-]+", "", s)
            return s or "img"

        safe_stem = slugify_light(original_stem)

        # ⚠️ Aquí estaba el fallo: NO usar subcategory.slug porque no existe.
        # Usamos el id de la subcategoría (y el slug de categoría si existe).
        cat_part = getattr(category, "slug", None) or str(category.id)
        base_id = f"{cat_part}_{subcategory.id}_{viewopt.id}_{safe_stem}_{uuid4().hex[:8]}"

        rel_input_path = f"uploads/{base_id}{ext or '.jpg'}"
        saved_path = default_storage.save(rel_input_path, ContentFile(upload.read()))
        abs_input_path = default_storage.path(saved_path)

        # --- Preparar prompt maestro (se mantiene oculto al usuario) ---
        master_prompt = viewopt.prompt or ""
        negative_prompt = getattr(viewopt, "negative_prompt", "") or ""
        strength = getattr(viewopt, "strength", 0.8)

        # === Aquí iría tu llamada real a la API de imagen (edit/inpaint) ===
        # Para no tocar tu integración, dejamos un “passthrough” que simplemente
        # publica la imagen subida y devuelve su URL como “resultado”.
        # Sustituye esta parte por tu llamada a OpenAI/Stable Diffusion/etc.
        output_rel_path = f"generated/{base_id}.jpg"
        with open(abs_input_path, "rb") as f:
            default_storage.save(output_rel_path, ContentFile(f.read()))
        result_url = default_storage.url(output_rel_path)

        # Registrar en BD
        GeneratedImage.objects.create(
            user=request.user,
            category=category,
            subcategory=subcategory,
            view_option=viewopt,
            input_image=rel_input_path,      # se guarda ruta relativa en el FileField
            output_image=output_rel_path,    # idem
            prompt_used=master_prompt,
            negative_prompt=negative_prompt,
            strength=strength,
        )

        messages.success(request, "Imagen generada correctamente.")
        return render(
            request,
            "products/upload_photo.html",
            {
                "category": category,
                "subcategory": subcategory,
                "viewoption": viewopt,
                "result_url": result_url,  # la plantilla ya lo sabe mostrar/descargar
            },
        )

    # GET: mostrar formulario de subida
    return render(
        request,
        "products/upload_photo.html",
        {
            "category": category,
            "subcategory": subcategory,
            "viewoption": viewopt,
        },
    )
