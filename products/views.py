
# products/views.py
import os
import io
import logging
import unicodedata
from uuid import uuid4
from pathlib import Path
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
from openai import OpenAI
import base64
from docx import Document

from .forms import SelectCategoryForm, UploadPhotoForm, ChooseViewForm, LogoForm

logger = logging.getLogger(__name__)
client = OpenAI()

# Acepta 'lineas' o 'Lineas'
_APP_DIR = Path(__file__).resolve().parent
_LINEAS_CANDIDATES = [_APP_DIR / "lineas", _APP_DIR / "Lineas"]
LINE_ROOT = next((p for p in _LINEAS_CANDIDATES if p.is_dir()), _LINEAS_CANDIDATES[0])

# ===========================
#   FUNCIONES AUXILIARES
# ===========================

def ensure_dirs():
    os.makedirs(os.path.join(settings.MEDIA_ROOT, 'uploads', 'input'), exist_ok=True)
    os.makedirs(os.path.join(settings.MEDIA_ROOT, 'uploads', 'output'), exist_ok=True)

def _normalize(s: str) -> str:
    s = (s or "").lower()
    s = s.replace("(", "").replace(")", "").replace("[", "").replace("]", "")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.strip()

def list_line_thumbnails(category: str, subcategory: str):
    try:
        normalized_target = _normalize(f"{category}_{subcategory}")
        if not Path(LINE_ROOT).exists():
            logger.warning("LINE_ROOT no existe: %s", LINE_ROOT)
            return []
        folder_path = None
        for folder in os.listdir(LINE_ROOT):
            if _normalize(folder) == normalized_target:
                folder_path = Path(LINE_ROOT) / folder
                break
        if folder_path is None or not folder_path.is_dir():
            logger.info("No encontrada carpeta de vistas para: %s", normalized_target)
            return []
        views = []
        for name in sorted(os.listdir(folder_path)):
            if name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                stem = os.path.splitext(name)[0]
                try:
                    num = int(stem)
                    views.append((num, str(folder_path / name)))
                except ValueError:
                    continue
        views.sort(key=lambda t: t[0])
        return views
    except Exception:
        logger.exception("Error listando miniaturas")
        return []

def copy_to_media_and_get_url(abs_path):
    ensure_dirs()
    try:
        with open(abs_path, 'rb') as f:
            data = f.read()
    except FileNotFoundError:
        logger.warning("Archivo de línea no encontrado: %s", abs_path)
        return None, None
    ext = os.path.splitext(abs_path)[1].lower().lstrip('.')
    fname = f'uploads/input/{uuid4()}.{ext}'
    media_abs = os.path.join(settings.MEDIA_ROOT, fname)
    os.makedirs(os.path.dirname(media_abs), exist_ok=True)
    with open(media_abs, 'wb') as out:
        out.write(data)
    return settings.MEDIA_URL + fname, media_abs

def add_white_border(img: Image.Image, border_px=50):
    return ImageOps.expand(img, border=border_px, fill='white')

def paste_logo_on_area(base_img: Image.Image, logo_img: Image.Image, rect):
    x, y, w, h = rect
    logo = logo_img.convert('RGBA')
    logo = logo.resize((max(1, int(w)), max(1, int(h))), Image.LANCZOS)
    base_rgba = base_img.convert('RGBA')
    base_rgba.paste(logo, (int(x), int(y)), logo)
    return base_rgba.convert('RGB')

def find_docx_for_view(source_folder: Path, chosen_view_num: int) -> Path:
    """
    Devuelve la RUTA del .docx que corresponde EXACTAMENTE a la vista elegida.
    Robusto ante espacios/mayúsculas: busca *_<num>.docx; si no, contiene _<num>.
    Si no encuentra, lanza FileNotFoundError (no hace fallback al _1).
    """
    folder = Path(source_folder)
    if not folder.is_dir():
        folder = folder.parent

    want = str(chosen_view_num)
    all_docx = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".docx"]

    def norm_name(p: Path) -> str:
        name = p.stem
        name = unicodedata.normalize("NFKD", name).lower().replace(" ", "")
        return name

    exact = [p for p in all_docx if norm_name(p).endswith(f"_{want}")]
    if exact:
        return exact[0]

    contains = [p for p in all_docx if f"_{want}" in norm_name(p)]
    if contains:
        return contains[0]

    # sufijo numérico al final
    for p in all_docx:
        n = norm_name(p)
        tail = ""
        for ch in reversed(n):
            if ch.isdigit():
                tail = ch + tail
            else:
                break
        if tail and tail == want:
            return p

    raise FileNotFoundError(
        f"No encontré un .docx para la vista {chosen_view_num} en {folder}. "
        f"Archivos .docx presentes: {[p.name for p in all_docx]}"
    )

def read_docx_text(path: Path) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs).strip()

def enhance_mockup(abs_path_in, abs_path_out):
    """
    Postpro ligero para dar más relieve y claridad al tejido + corrección gamma (Photoshop 1.30).
    """
    img = Image.open(abs_path_in).convert('RGB')
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))
    img = ImageEnhance.Contrast(img).enhance(1.06)
    img = ImageEnhance.Sharpness(img).enhance(1.08)
    gamma = 1 / 1.30  # equivalente a '1.30' en Niveles de Photoshop (centro)
    lut = [min(255, int((i / 255.0) ** gamma * 255 + 0.5)) for i in range(256)]
    img = img.point(lut * 3)
    img.save(abs_path_out, quality=95)

# ===========================
#          VISTAS
# ===========================

def select_category(request):
    if request.method == 'POST':
        form = SelectCategoryForm(request.POST)
        if form.is_valid():
            request.session['selection'] = form.cleaned_data
            return redirect('products:upload_photo')
    else:
        form = SelectCategoryForm()
    return render(request, 'products/select_category.html', {'form': form})

def upload_photo(request):
    try:
        selection = request.session.get('selection')
        if not selection:
            messages.error(request, "Vuelve a iniciar la selección.")
            return redirect('products:select_category')

        category = selection.get('category', '')
        subcategory = selection.get('subcategory', '')

        views_found = list_line_thumbnails(category, subcategory)
        view_numbers = [num for num, _ in views_found]

        if request.method == 'POST':
            upload_form = UploadPhotoForm(request.POST, request.FILES)
            choose_view_form = ChooseViewForm(request.POST, view_numbers=view_numbers)
            logo_form = LogoForm(request.POST, request.FILES)

            if not views_found:
                messages.error(request, "No se han encontrado vistas para esta categoría/subcategoría.")
                return render(request, 'products/upload_photo.html', {
                    'selection': selection,
                    'upload_form': upload_form,
                    'choose_view_form': choose_view_form,
                    'logo_form': logo_form,
                    'thumbnails': [],
                })

            if upload_form.is_valid():
                ensure_dirs()
                # 1) Guardar foto del cliente
                client_file = upload_form.cleaned_data['client_photo']
                client_ext = os.path.splitext(client_file.name)[1].lower().lstrip('.')
                input_rel = f'uploads/input/{uuid4()}.{client_ext}'
                input_abs = os.path.join(settings.MEDIA_ROOT, input_rel)
                os.makedirs(os.path.dirname(input_abs), exist_ok=True)
                with open(input_abs, 'wb') as out:
                    for chunk in client_file.chunks():
                        out.write(chunk)
                client_url = settings.MEDIA_URL + input_rel

                # 2) Leer vista del POST (obligatoria)
                raw_view = (request.POST.get('view_number') or "").strip()
                if not (raw_view.isdigit() and int(raw_view) in view_numbers):
                    messages.error(request, "Selecciona una vista válida.")
                    return redirect('products:upload_photo')
                chosen_view_num = int(raw_view)
                logger.info(f"[upload_photo] Vista seleccionada por el usuario: {chosen_view_num}")

                # 3) Imagen de líneas elegida
                chosen_abs = None
                for num, path in views_found:
                    if num == chosen_view_num:
                        chosen_abs = path
                        break
                if not chosen_abs:
                    messages.error(request, 'No se encontró la vista seleccionada.')
                    return redirect('products:upload_photo')

                # 4) Elegir el .docx EXACTO y guardar su ruta en sesión
                prompt_docx = find_docx_for_view(Path(chosen_abs).parent, chosen_view_num)
                logger.info(f"[upload_photo] Prompt DOCX elegido: {prompt_docx}")

                # Copiar miniatura a media (opcional)
                line_url, line_abs = copy_to_media_and_get_url(chosen_abs)
                if not line_abs:
                    messages.error(request, "No se pudo preparar la vista seleccionada.")
                    return redirect('products:upload_photo')

                # 5) Guardar TODO en sesión; no se volverá a deducir nada más tarde
                request.session['work'] = {
                    'client_input_rel': input_rel,
                    'client_url': client_url,
                    'line_abs': line_abs,
                    'line_url': line_url,
                    'chosen_view_num': chosen_view_num,
                    'prompt_docx_path': str(prompt_docx),   # <- RUTA FIJA DEL .DOCX
                }

                return redirect('products:result')

        else:
            upload_form = UploadPhotoForm()
            choose_view_form = ChooseViewForm(view_numbers=view_numbers)
            logo_form = LogoForm()

        # Miniaturas
        thumbs = []
        for num, abs_path in views_found:
            url, _ = copy_to_media_and_get_url(abs_path)
            if url:
                thumbs.append((num, url))

        return render(request, 'products/upload_photo.html', {
            'selection': selection,
            'upload_form': upload_form,
            'choose_view_form': choose_view_form,
            'logo_form': logo_form,
            'thumbnails': thumbs,
        })

    except Exception:
        logger.exception("Fallo inesperado en upload_photo")
        messages.error(request, "Ha ocurrido un error al cargar la página. Inténtalo de nuevo.")
        return redirect('products:select_category')

# === LLAMADA A OPENAI: edit (prompt + imagen del cliente) ===
def _call_openai_edit(client_abs, prompt_text):
    with open(client_abs, "rb") as f:
        resp = client.images.edit(
            model="gpt-image-1",
            image=[f],
            prompt=prompt_text,
            size="1024x1024",
        )
    img_b64 = resp.data[0].b64_json
    if not img_b64:
        raise ValueError("OpenAI no devolvió imagen en b64_json.")
    return base64.b64decode(img_b64)

# ==========================================

def _call_openai_logo(result1_abs, logo_abs, rect_pixels):
    base = Image.open(result1_abs).convert('RGB')
    logo = Image.open(logo_abs).convert('RGBA')
    result = paste_logo_on_area(base, logo, rect_pixels)
    buf = io.BytesIO()
    result.save(buf, format='JPEG', quality=95)
    return buf.getvalue()

def result_view(request):
    try:
        work = request.session.get('work')
        if not work:
            messages.error(request, "Vuelve a iniciar la selección.")
            return redirect('products:select_category')

        ensure_dirs()

        client_rel = work['client_input_rel']
        client_abs = os.path.join(settings.MEDIA_ROOT, client_rel)
        chosen_view_num = int(work['chosen_view_num'])

        # Usar SIEMPRE el .docx guardado en sesión
        prompt_docx_path = work.get('prompt_docx_path')
        if not prompt_docx_path or not os.path.isfile(prompt_docx_path):
            messages.error(request, "No se encontró el prompt asociado a la vista elegida.")
            return redirect('products:upload_photo')
        prompt_text = read_docx_text(Path(prompt_docx_path))
        prompt_name = os.path.basename(prompt_docx_path)
        logger.info(f"[result_view] Usando prompt fijo: {prompt_name} (vista {chosen_view_num})")

        # Llamada a OpenAI con la imagen subida y el prompt
        result1_bytes = _call_openai_edit(client_abs=client_abs, prompt_text=prompt_text)

        # Guardar imagen base
        result1_rel = f'uploads/output/Resultado_1_{uuid4()}.jpg'
        result1_abs = os.path.join(settings.MEDIA_ROOT, result1_rel)
        with open(result1_abs, 'wb') as f:
            f.write(result1_bytes)

        # Post-procesado
        post_rel = f'uploads/output/Resultado_1_post_{uuid4()}.jpg'
        post_abs = os.path.join(settings.MEDIA_ROOT, post_rel)
        enhance_mockup(result1_abs, post_abs)
        result1_url = settings.MEDIA_URL + post_rel
        final_url = result1_url

        # Limpiar sesión temporal
        request.session.pop('work', None)
        request.session.pop('logo', None)

        return render(request, 'products/result.html', {
            'result1_url': result1_url,
            'final_url': final_url,
            'used_logo': False,
            'used_view': chosen_view_num,
            'prompt_name': prompt_name,
        })
    except Exception:
        logger.exception("Fallo inesperado en result_view")
        messages.error(request, "Ha ocurrido un error generando el resultado.")
        return redirect('products:upload_photo')
