# products/views.py
import os
import json
import uuid
import logging
from glob import glob
from pathlib import Path

from django import forms
from django.conf import settings
from django.core.files.storage import default_storage
from django.shortcuts import render, redirect

from .forms import SelectCategoryForm

logger = logging.getLogger("django")

# ---- Form simple para subir imagen ----
class UploadForm(forms.Form):
    image = forms.ImageField(label="Selecciona una imagen", required=True)


# ---- Utilidad: crear carpetas solo si se puede escribir ----
def ensure_dirs():
    base = Path(settings.MEDIA_ROOT)
    if os.access(base, os.W_OK):
        for sub in ("uploads/input", "uploads/output", "uploads/tmp"):
            (base / sub).mkdir(parents=True, exist_ok=True)
    else:
        logger.warning(f"[ensure_dirs] MEDIA_ROOT no escribible: {base}")


# ---- Paso 1: selección inicial ----
def select_category(request):
    ensure_dirs()
    if request.method == "POST":
        form = SelectCategoryForm(request.POST)
        if form.is_valid():
            request.session["selection"] = form.cleaned_data
            request.session.modified = True
            return redirect("upload_photo")
    else:
        form = SelectCategoryForm()
    return render(request, "products/select_category.html", {"form": form})


# ---- Localiza miniaturas en static o media (si existen) ----
def _find_thumbnails():
    thumbs = []

    # 1) En static del proyecto
    static_dir = Path(settings.BASE_DIR) / "products" / "static" / "products" / "lineas"
    for pattern in ("**/*.png", "**/*.jpg", "**/*.jpeg", "**/*.webp"):
        thumbs += [p for p in glob(str(static_dir / pattern), recursive=True)]

    # 2) En media (si has subido lineas al disco)
    media_dir = Path(settings.MEDIA_ROOT) / "lineas"
    if media_dir.exists():
        for pattern in ("**/*.png", "**/*.jpg", "**/*.jpeg", "**/*.webp"):
            thumbs += [p for p in glob(str(media_dir / pattern), recursive=True)]

    # Normalizamos a rutas relativas “/static/…” o “/media/…”
    rel_urls = []
    for p in thumbs:
        pth = Path(p)
        try:
            if "static/products/lineas" in p:
                # servir por static
                rel = "/static/products/lineas/" + str(pth).split("static/products/lineas/")[-1].replace("\\", "/")
                rel_urls.append(rel)
            elif "/media/" in p.replace("\\", "/"):
                rel = p.split("/media/")[-1]
                rel_urls.append(f"{settings.MEDIA_URL.rstrip('/')}/{rel}")
            elif str(pth).startswith(str(media_dir)):
                rel = str(pth.relative_to(media_dir)).replace("\\", "/")
                rel_urls.append(f"{settings.MEDIA_URL.rstrip('/')}/lineas/{rel}")
        except Exception as e:
            logger.warning(f"[find_thumbnails] no se pudo normalizar {p}: {e}")
    # Únicas y ordenadas
    seen, out = set(), []
    for u in rel_urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


# ---- Paso 2: subir imagen ----
def upload_photo(request):
    ensure_dirs()
    selection = request.session.get("selection")
    if not selection:
        return redirect("select_category")

    thumbnails = _find_thumbnails()

    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                image = form.cleaned_data["image"]
                rel_path = default_storage.save(os.path.join("uploads/input", image.name), image)
                input_path = os.path.join(settings.MEDIA_ROOT, rel_path)

                job_id = str(uuid.uuid4())
                tmp_file = os.path.join(settings.MEDIA_ROOT, "uploads/tmp", f"{job_id}.json")
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump({"selection": selection, "input_path": input_path, "output_path": ""}, f)

                request.session["job_id"] = job_id
                request.session.modified = True
                return redirect("processing")
            except Exception as e:
                logger.error(f"[upload_photo] Error guardando imagen: {e}", exc_info=True)
                return render(
                    request,
                    "products/upload_photo.html",
                    {"form": form, "selection": selection, "thumbnails": thumbnails, "error": str(e)},
                    status=400,
                )
        else:
            # Form inválido: re-mostramos con errores (sin 500)
            return render(
                request,
                "products/upload_photo.html",
                {"form": form, "selection": selection, "thumbnails": thumbnails},
                status=400,
            )
    else:
        form = UploadForm()

    return render(
        request,
        "products/upload_photo.html",
        {"form": form, "selection": selection, "thumbnails": thumbnails},
    )


# ---- Paso 3: procesamiento (placeholder seguro) ----
def processing(request):
    ensure_dirs()
    job_id = request.session.get("job_id")
    if not job_id:
        return redirect("select_category")

    tmp_file = os.path.join(settings.MEDIA_ROOT, "uploads/tmp", f"{job_id}.json")
    if not os.path.exists(tmp_file):
        return redirect("select_category")

    with open(tmp_file, "r", encoding="utf-8") as f:
        job = json.load(f)

    output_path = os.path.join(settings.MEDIA_ROOT, "uploads/output", f"{job_id}.png")

    # Placeholder: crea una imagen 1x1 para validar el flujo
    try:
        from PIL import Image
        img = Image.new("RGB", (1, 1), (255, 255, 255))
        img.save(output_path)
    except Exception as e:
        logger.error(f"[processing] No se pudo generar PNG placeholder: {e}")
        # Fallback binario mínimo
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(
                b"\x89PNG\r\n\x1a\n"
                b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
                b"\x00\x00\x00\x0AIEND\xaeB`\x82"
            )

    job["output_path"] = output_path
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(job, f)

    request.session["job_id"] = job_id
    request.session.modified = True
    return redirect("result")


# ---- Paso 4: resultado ----
def result(request):
    ensure_dirs()
    job_id = request.session.get("job_id")
    if not job_id:
        return redirect("select_category")

    tmp_file = os.path.join(settings.MEDIA_ROOT, "uploads/tmp", f"{job_id}.json")
    if not os.path.exists(tmp_file):
        return redirect("select_category")

    with open(tmp_file, "r", encoding="utf-8") as f:
        job = json.load(f)

    return render(
        request,
        "products/result.html",
        {"output_path": job.get("output_path"), "selection": job.get("selection", {})},
    )
