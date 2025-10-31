import os
import json
import uuid
import base64
import logging
import unicodedata
from glob import glob
from pathlib import Path

from django import forms
from django.conf import settings
from django.core.files.storage import default_storage
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseForbidden

from .forms import SelectCategoryForm
from docx import Document
from PIL import Image
from zipfile import ZipFile, BadZipFile

logger = logging.getLogger("django")


# =========================
# Formularios
# =========================
class UploadForm(forms.Form):
    image = forms.ImageField(label="Selecciona una imagen", required=True)
    asset_id = forms.CharField(widget=forms.HiddenInput(), required=True)


class UploadLineasForm(forms.Form):
    zipfile = forms.FileField(label="ZIP con carpetas de líneas")


# =========================
# Utilidades
# =========================
def ensure_dirs():
    base = Path(settings.MEDIA_ROOT)
    for sub in ("uploads/input", "uploads/output", "uploads/tmp", "lineas"):
        (base / sub).mkdir(parents=True, exist_ok=True)


def _simplify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    out = []
    for ch in s:
        if ch.isalnum() or ch in (" ", "_", "-"):
            out.append(ch)
    return "".join(out).replace("_", " ").replace("-", " ").strip()


def _asset_bases():
    # 1) PRODUCCIÓN /opt/render/project/src/media/lineas (persistente en Render)
    yield settings.LINEAS_ROOT
    # 2) Desarrollo local (opcional)
    yield Path(settings.BASE_DIR) / "products" / "lineas"


def _read_prompt_from_dir(line_dir: Path) -> str:
    files = sorted(glob(str(line_dir / "*.docx")))
    if not files:
        return "Genera una imagen del producto según la vista seleccionada."
    try:
        doc = Document(files[0])
        text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
        return text or "Genera una imagen del producto según la vista seleccionada."
    except Exception as e:
        logger.warning(f"No se pudo leer DOCX {files[0]}: {e}")
        return "Genera una imagen del producto según la vista seleccionada."


def _copy_to_media(src: Path) -> str:
    """
    Copia miniaturas a MEDIA_ROOT/lineas/... para que sean accesibles como /media/lineas/...
    Devuelve la URL resultante.
    """
    ensure_dirs()
    rel = src.name
    for base in _asset_bases():
        try:
            if str(src).startswith(str(base)):
                rel = str(src.relative_to(base))
                break
        except Exception:
            pass
    dest = Path(settings.MEDIA_ROOT) / "lineas" / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        try:
            # copia binaria
            with open(src, "rb") as fin, open(dest, "wb") as fout:
                fout.write(fin.read())
        except Exception as e:
            logger.warning(f"No se pudo copiar {src} -> {dest}: {e}")
    return f"{settings.MEDIA_URL.rstrip('/')}/lineas/{rel}".replace("\\", "/")


def _find_assets(selection: dict):
    """
    Busca carpeta que contenga categoria y subcategoria (ignorando acentos/espacios/mayúsculas)
    y devuelve miniaturas + prompt.
    """
    want_cat = _simplify(selection.get("categoria", ""))
    want_sub = _simplify(selection.get("subcategoria", ""))

    assets = []
    patterns = ("*.png", "*.jpg", "*.jpeg", "*.webp")
    processed_images = set()  # Para evitar duplicados

    for base in _asset_bases():
        if not base.exists():
            continue
        for d in base.iterdir():
            if not d.is_dir():
                continue
            name_s = _simplify(d.name)
            if want_cat in name_s and want_sub in name_s:
                prompt = _read_prompt_from_dir(d)
                for pat in patterns:
                    for fp in sorted(d.glob(pat)):
                        # Solo procesar cada imagen una vez
                        img_name = fp.stem  # nombre sin extensión
                        if img_name not in processed_images:
                            processed_images.add(img_name)
                            assets.append({
                                "id": asset_id,
                                "thumb_url": _copy_to_media(fp),
                                "prompt": prompt,
                                "source_file": str(fp),
                            })
    return assets


def _media_url_from_path(abs_path: str) -> str:
    rel = os.path.relpath(abs_path, settings.MEDIA_ROOT)
    return f"{settings.MEDIA_URL.rstrip('/')}/{rel.replace(os.sep, '/')}"


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

    assets = _find_assets(selection)

    # Si hay assets, el usuario debe elegir uno; si no, igual puede subir su foto (pero pedimos asset por consistencia)
    initial = {}
    form = UploadForm(request.POST or None, request.FILES or None, initial=initial)

    error_msg = ""
    if request.method == "POST":
        # Validación personalizada:
        #  - Debe haber asset elegido
        #  - Imagen obligatoria y válida (formato y tamaño)
        chosen_id = request.POST.get("asset_choice") or request.POST.get("asset_id")
        print(f"DEBUG: chosen_id = {chosen_id}")
        print(f"DEBUG: POST data = {request.POST}")
        print(f"DEBUG: Available assets = {[a['id'] for a in assets]}")
        
        if not chosen_id:
            error_msg = "Debes seleccionar una vista."
        elif "image" not in request.FILES:
            error_msg = "Debes subir una imagen."
        else:
            image_file = request.FILES["image"]
            # Tamaño de archivo
            max_mb = 15
            if image_file.size > max_mb * 1024 * 1024:
                error_msg = f"La imagen excede {max_mb} MB."
            else:
                # Validar dimensiones mínimas (ej. 512x512)
                try:
                    image_file.seek(0)  # MOVER AQUÍ AL INICIO
                    im = Image.open(image_file)
                    w, h = im.size
                    if min(w, h) < 512:
                        error_msg = "La imagen es demasiado pequeña. Mínimo 512x512."
                    # NO CERRAR: im.close()
                except Exception:
                    error_msg = "Archivo de imagen no válido."

        if not error_msg:
            # Guardar imagen subida
            image_file.seek(0)  # Resetear de nuevo antes de guardar
            rel_path = default_storage.save(os.path.join("uploads/input", image_file.name), image_file)
            input_path = os.path.join(settings.MEDIA_ROOT, rel_path)

            # Buscar prompt del asset elegido
            chosen = next((a for a in assets if a["id"] == chosen_id), None)
            if not chosen:
                error_msg = "La vista elegida no es válida."
            else:
                job_id = str(uuid.uuid4())
                tmp_file = Path(settings.MEDIA_ROOT) / "uploads" / "tmp" / f"{job_id}.json"
                tmp_file.parent.mkdir(parents=True, exist_ok=True)
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "selection": selection,
                        "input_path": input_path,
                        "prompt": chosen["prompt"],
                    }, f)
                request.session["job_id"] = job_id
                request.session.modified = True
                return redirect("processing")

    return render(
        request,
        "products/upload_photo.html",
        {"form": form, "selection": selection, "assets": assets, "error": error_msg},
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

    prompt = job.get("prompt") or "Genera una imagen del producto."
    input_path = job.get("input_path")
    output_path = Path(settings.MEDIA_ROOT) / "uploads" / "output" / f"{job_id}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Requerir API KEY
    api_key = (getattr(settings, "OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return render(request, "products/error.html", {
            "message": "OPENAI_API_KEY no está configurada. Configúrala en Render → Environment."
        }, status=500)

    try:
        # Llamada real a OpenAI (gpt-image-1).
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        with open(input_path, "rb") as fin:
            resp = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size="1024x1024",
                image=fin,
            )

        b64 = resp.data[0].b64_json
        img_bytes = base64.b64decode(b64)
        with open(output_path, "wb") as fout:
            fout.write(img_bytes)

        output_url = _media_url_from_path(str(output_path))

        job["output_path"] = str(output_path)
        job["output_url"] = output_url
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(job, f)

        request.session["job_id"] = job_id
        return redirect("result")

    except Exception as e:
        logger.error(f"[processing] Error llamando a OpenAI: {e}", exc_info=True)
        return render(request, "products/error.html", {
            "message": f"Error al generar la imagen con OpenAI: {e}"
        }, status=500)


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
        {
            "output_url": job.get("output_url"),
            "output_path": job.get("output_path"),
            "selection": job.get("selection", {}),
        },
    )


# ====== Carga de LINEAS por ZIP (protegido por clave) ======
def upload_lineas_zip(request):
    """
    Subida segura de un ZIP con líneas:
    - Protegida por una clave en env: LINEAS_UPLOAD_KEY
    - Extrae el ZIP en settings.LINEAS_ROOT
    - No requiere tocar Git; pensada para Render (disco /data)
    """
    required_key = os.environ.get("LINEAS_UPLOAD_KEY", "").strip()
    key = request.GET.get("key", "").strip() or request.POST.get("key", "").strip()
    if not required_key or key != required_key:
        return HttpResponseForbidden("No autorizado")

    if request.method == "POST":
        form = UploadLineasForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data["zipfile"]
            dest = settings.LINEAS_ROOT
            dest.mkdir(parents=True, exist_ok=True)
            try:
                with ZipFile(f) as z:
                    z.extractall(dest)
                return HttpResponse("OK: líneas actualizadas en /data/lineas")
            except BadZipFile:
                return HttpResponse("Archivo ZIP inválido", status=400)
        return HttpResponse("Solicitud inválida", status=400)

    # Form simple para subir desde navegador si lo necesitas
    html = """
    <h3>Subir líneas (ZIP)</h3>
    <form method="post" enctype="multipart/form-data">
      <input type="hidden" name="key" value="{key}">
      <input type="file" name="zipfile" accept=".zip" required>
      <button type="submit">Subir</button>
    </form>
    """
    return HttpResponse(html.format(key=required_key))