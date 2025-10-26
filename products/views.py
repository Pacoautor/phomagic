# products/views.py
import os
import json
import uuid
import shutil
import logging
from glob import glob
from pathlib import Path

from django import forms
from django.conf import settings
from django.core.files.storage import default_storage
from django.shortcuts import render, redirect

from .forms import SelectCategoryForm
from docx import Document  # para leer prompts .docx

logger = logging.getLogger("django")


# =========================
# Formularios
# =========================
class UploadForm(forms.Form):
    image = forms.ImageField(label="Selecciona una imagen", required=False)
    asset_id = forms.CharField(widget=forms.HiddenInput(), required=False)  # miniatura elegida


# =========================
# Utilidades de directorios
# =========================
def ensure_dirs():
    base = Path(settings.MEDIA_ROOT)
    # MEDIA_ROOT ahora apunta a BASE_DIR/media (escribible)
    for sub in ("uploads/input", "uploads/output", "uploads/tmp", "lineas"):
        (base / sub).mkdir(parents=True, exist_ok=True)


def _norm(s: str) -> str:
    return (
        s.replace("/", " ")
        .replace("\\", " ")
        .strip()
        .replace("  ", " ")
        .replace(" ", "_")
    )


def _asset_bases():
    """
    De dónde leeremos las líneas:
    1) TU carpeta real: products/lineas/
    2) (opcional) static/products/lineas/
    3) (opcional) media/lineas/
    """
    return [
        Path(settings.BASE_DIR) / "products" / "lineas",
        Path(settings.BASE_DIR) / "products" / "static" / "products" / "lineas",
        Path(settings.MEDIA_ROOT) / "lineas",
    ]


def _copy_to_media_if_needed(src: Path) -> str:
    """
    Si la miniatura está en products/lineas o en static, la copiamos a MEDIA_ROOT/lineas
    para que sea servida como /media/lineas/...
    Devuelve la URL /media/... resultante.
    """
    ensure_dirs()
    rel = None

    # Calcula una ruta relativa estable dentro de /media/lineas/
    for base in _asset_bases():
        try:
            if str(src).startswith(str(base)):
                rel = src.relative_to(base)
                break
        except Exception:
            pass

    if rel is None:
        # fallback: solo el nombre
        rel = src.name

    dest = Path(settings.MEDIA_ROOT) / "lineas" / str(rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not dest.exists():
            shutil.copyfile(src, dest)
    except Exception as e:
        logger.warning(f"No se pudo copiar {src} a {dest}: {e}")

    url = f"{settings.MEDIA_URL.rstrip('/')}/lineas/{rel}".replace("\\", "/")
    return url


def _read_prompt_from_dir(line_dir: Path) -> str:
    """
    Lee el primer .docx de la carpeta de la línea. Si no hay, devuelve un prompt genérico.
    """
    docx_files = sorted(glob(str(line_dir / "*.docx")))
    if not docx_files:
        return "Genera una imagen de producto según la miniatura elegida, sobre fondo indicado."

    text_parts = []
    try:
        doc = Document(docx_files[0])
        for p in doc.paragraphs:
            if p.text.strip():
                text_parts.append(p.text.strip())
        return "\n".join(text_parts).strip() or "Genera una imagen de producto según la miniatura elegida."
    except Exception as e:
        logger.warning(f"No se pudo leer DOCX {docx_files[0]}: {e}")
        return "Genera una imagen de producto según la miniatura elegida."


def _find_assets(selection: dict):
    """
    Busca miniaturas y prompt en products/lineas/<Categoria>_<Subcategoria>/
    Devuelve lista de dicts: {"id": str, "thumb_url": str, "prompt": str}
    """
    cat = selection.get("categoria", "")
    sub = selection.get("subcategoria", "")
    dir_name = f"{_norm(cat)}_{_norm(sub)}"

    assets = []
    patterns = ("*.png", "*.jpg", "*.jpeg", "*.webp")

    for base in _asset_bases():
        line_dir = base / dir_name
        if not line_dir.exists():
            continue

        prompt = _read_prompt_from_dir(line_dir)

        for pat in patterns:
            for fp in sorted(line_dir.glob(pat)):
                thumb_url = _copy_to_media_if_needed(fp)
                assets.append(
                    {
                        "id": str(uuid.uuid4()),
                        "thumb_url": thumb_url,
                        "prompt": prompt,
                        "source_file": str(fp),
                    }
                )

    return assets


# =========================
# Vistas
# =========================
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


def upload_photo(request):
    ensure_dirs()
    selection = request.session.get("selection")
    if not selection:
        return redirect("select_category")

    assets = _find_assets(selection)  # miniaturas + prompt
    form = UploadForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        # 1) Si suben imagen, la guardamos
        input_path = ""
        if form.cleaned_data.get("image"):
            image = form.cleaned_data["image"]
            rel_path = default_storage.save(os.path.join("uploads/input", image.name), image)
            input_path = os.path.join(settings.MEDIA_ROOT, rel_path)

        # 2) Si seleccionan una miniatura, cogemos su prompt
        chosen_id = form.cleaned_data.get("asset_id")
        chosen = next((a for a in assets if a["id"] == chosen_id), None)
        prompt = chosen["prompt"] if chosen else "Prompt por defecto para generación de imagen."

        job_id = str(uuid.uuid4())
        tmp_file = Path(settings.MEDIA_ROOT) / "uploads" / "tmp" / f"{job_id}.json"
        tmp_file.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump({"selection": selection, "input_path": input_path, "prompt": prompt}, f)

        request.session["job_id"] = job_id
        request.session.modified = True
        return redirect("processing")

    return render(
        request,
        "products/upload_photo.html",
        {"form": form, "selection": selection, "assets": assets},
    )


def processing(request):
    ensure_dirs()
    job_id = request.session.get("job_id")
    if not job_id:
        return redirect("select_category")

    tmp_file = Path(settings.MEDIA_ROOT) / "uploads" / "tmp" / f"{job_id}.json"
    if not tmp_file.exists():
        return redirect("select_category")

    with open(tmp_file, "r", encoding="utf-8") as f:
        job = json.load(f)

    # Generamos una salida dummy para cerrar el flujo (sustituiremos por tu lógica real)
    output_path = Path(settings.MEDIA_ROOT) / "uploads" / "output" / f"{job_id}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image
        img = Image.new("RGB", (600, 600), (255, 255, 255))
        img.save(output_path)
    except Exception as e:
        logger.error(f"No se pudo crear PNG: {e}")
        with open(output_path, "wb") as f:
            f.write(
                b"\x89PNG\r\n\x1a\n"
                b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
                b"\x00\x00\x00\x0AIEND\xaeB`\x82"
            )

    job["output_path"] = str(output_path)
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(job, f)

    request.session["job_id"] = job_id
    return redirect("result")


def result(request):
    ensure_dirs()
    job_id = request.session.get("job_id")
    if not job_id:
        return redirect("select_category")

    tmp_file = Path(settings.MEDIA_ROOT) / "uploads" / "tmp" / f"{job_id}.json"
    if not tmp_file.exists():
        return redirect("select_category")

    with open(tmp_file, "r", encoding="utf-8") as f:
        job = json.load(f)

    return render(
        request,
        "products/result.html",
        {"output_path": job.get("output_path"), "selection": job.get("selection", {})},
    )

