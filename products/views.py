from django.contrib import messages

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
from openai import OpenAI

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
    yield settings.LINEAS_ROOT
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
            with open(src, "rb") as fin, open(dest, "wb") as fout:
                fout.write(fin.read())
        except Exception as e:
            logger.warning(f"No se pudo copiar {src} -> {dest}: {e}")
    return f"{settings.MEDIA_URL.rstrip('/')}/lineas/{rel}".replace("\\", "/")


def _find_assets(selection: dict):
    want_cat = _simplify(selection.get("categoria", ""))
    want_sub = _simplify(selection.get("subcategoria", ""))
    assets = []
    patterns = ("*.png", "*.jpg", "*.jpeg", "*.webp")
    processed_images = set()

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
                        img_name = fp.stem
                        if img_name not in processed_images:
                            processed_images.add(img_name)
                            asset_id = str(hash(str(fp)))
                            assets.append({
                                "id": asset_id,
                                "thumb_url": _copy_to_media(fp),
                                "prompt": prompt,
                                "source_file": str(fp),
                            })
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
    """
    Página donde el usuario sube la imagen después de elegir la vista (1, 2, 3...)
    """
    selection = request.session.get("selection")

    if not selection:
        return redirect("select_category")

    # ⚡️ Si el usuario ha seleccionado una vista, guardarla en sesión
    if request.method == "POST":
        selected_view = request.POST.get("selected_view")
        if selected_view:
            request.session["selected_view"] = selected_view  # <- Guardamos la vista elegida
            return redirect("upload_photo")

        # Si el usuario sube la imagen
        if "image" in request.FILES:
            image = request.FILES["image"]
            fs = FileSystemStorage()
            filename = fs.save(image.name, image)
            uploaded_file_url = fs.url(filename)
            request.session["uploaded_file_url"] = uploaded_file_url
            return redirect("processing")

    # ⚡️ Si no hay una vista seleccionada, mostramos aviso
    selected_view = request.session.get("selected_view", None)
    if not selected_view:
        messages.warning(request, "Selecciona una vista antes de subir la imagen.")

    assets = _find_assets(selection)

    return render(request, "upload_photo.html", {
        "selection": selection,
        "assets": assets,
        "selected_view": selected_view
    })
def processing(request):
    """
    Procesa la imagen subida por el usuario usando la vista seleccionada.
    """
    ensure_dirs()
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return render(request, "error.html", {"error": "Falta la clave de API de OpenAI."})

    try:
        # 🧠 Recuperamos información guardada en la sesión
        job_id = request.session.get("job_id")
        selection = request.session.get("selection")
        selected_view = request.session.get("selected_view")  # ⚡ Recuperamos la vista elegida
        uploaded_file_url = request.session.get("uploaded_file_url")

        if not uploaded_file_url:
            return render(request, "error.html", {"error": "No se encontró la imagen subida."})

        # Si no hay vista seleccionada, usar la 1 por defecto
        if not selected_view:
            selected_view = "1"

        # Localizamos la carpeta correspondiente a la vista elegida
        base_path = Path(settings.LINEAS_ROOT) / selection
        assets_folder = base_path / selected_view

        if not assets_folder.exists():
            return render(request, "error.html", {"error": f"No se encontró la carpeta de la vista seleccionada ({selected_view})."})

        # 🧩 Buscar archivos .txt y .png dentro de la carpeta
        txt_files = list(assets_folder.glob("*.txt"))
        png_files = list(assets_folder.glob("*.png"))

        if not txt_files or not png_files:
            return render(request, "error.html", {"error": "Faltan los archivos necesarios (.txt o .png) en la vista seleccionada."})

        # Leemos el prompt del archivo .txt
        with open(txt_files[0], "r", encoding="utf-8") as f:
            prompt = f.read().strip()

        # 📸 Ruta de la imagen subida
        input_path = str(Path(settings.MEDIA_ROOT) / uploaded_file_url.replace("/media/", ""))

        if not os.path.exists(input_path):
            return render(request, "error.html", {"error": "No se encontró la imagen subida en el servidor."})

        # Convertimos a RGBA si es necesario
        img = Image.open(input_path)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        rgba_path = str(Path(input_path).with_suffix(".png"))
        img.save(rgba_path, "PNG")
        input_path = rgba_path

        # 🔥 Llamada a OpenAI con la vista elegida
        client = OpenAI(api_key=api_key)
        with open(input_path, "rb") as image_file:
            response = client.images.edit(
                model="gpt-image-1",
                image=image_file,
                prompt=prompt,
                size="1024x1024"
            )

        # Guardamos la imagen generada
        image_url = response.data[0].url
        request.session["generated_image_url"] = image_url

        return render(request, "result.html", {
            "image_url": image_url,
            "selected_view": selected_view,
            "selection": selection
        })

    except Exception as e:
        return render(request, "error.html", {"error": f"Error al procesar la imagen: {str(e)}"})

def result(request):
    job_id = request.session.get("job_id")
    tmp_file = Path(settings.MEDIA_ROOT) / "uploads" / "tmp" / f"{job_id}.json"
    if not tmp_file.exists():
        return redirect("select_category")

    with open(tmp_file, "r", encoding="utf-8") as f:
        job = json.load(f)

    return render(request, "products/result.html", {"output_url": job.get("output_url")})


def upload_lineas_zip(request):
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
                return HttpResponse("OK: líneas actualizadas")
            except BadZipFile:
                return HttpResponse("Archivo ZIP inválido", status=400)
        return HttpResponse("Solicitud inválida", status=400)

    return HttpResponse("<h3>Subir líneas ZIP</h3>")
