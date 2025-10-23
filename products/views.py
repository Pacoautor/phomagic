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

def load_prompt_for_view(source_folder: Path, chosen_view_num: int) -> str:
    """
    Busca un archivo .docx en la carpeta de la VISTA ORIGINAL (no en media/),
    por ejemplo Prompt_camiseta_1.docx, y devuelve su texto.
    """
    folder = Path(source_folder)
    if not folder.is_dir():
        folder = folder.parent
    candidates = list(folder.glob(f"*_{chosen_view_num}.docx")) or list(folder.glob("*.docx"))
    if not candidates:
        raise FileNotFoundError(f"No se encontró prompt .docx en {folder}")
    doc = Document(candidates[0])
    text = "\n".join(p.text for p in doc.paragraphs).strip()
    logger.info(f"Usando prompt: {candidates[0].name} en {folder}")
    return text

def enhance_mockup(abs_path_in, abs_path_out):
    """
    Postpro ligero para dar más relieve y claridad al tejido + corrección gamma (Photoshop 1.30).
    - Micro-contraste (UnsharpMask)
    - Contraste y nitidez suaves
    - Gamma equivalente a Niveles 1.30 en PS (aclara medios tonos)
    """
    # Cargar imagen
    img = Image.open(abs_path_in).convert('RGB')

    # Claridad local (micro-contraste)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))

    # Ajustes globales suaves
    img = ImageEnhance.Contrast(img).enhance(1.06)
    img = ImageEnhance.Sharpness(img).enhance(1.08)

    # Corrección gamma: Photoshop 1.30 aclara -> usar 1/1.30 ≈ 0.77
    gamma = 1 / 1.30
    lut = [min(255, int((i / 255.0) ** gamma * 255 + 0.5)) for i in range(256)]
    img = img.point(lut * 3)  # aplicar a R,G,B

    # Guardar
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

            if upload_form.is_valid() and choose_view_form.is_valid():
                ensure_dirs()
                # Guardar foto del cliente
                client_file = upload_form.cleaned_data['client_photo']
                client_ext = os.path.splitext(client_file.name)[1].lower().lstrip('.')
                input_rel = f'uploads/input/{uuid4()}.{client_ext}'
                input_abs = os.path.join(settings.MEDIA_ROOT, input_rel)
                os.makedirs(os.path.dirname(input_abs), exist_ok=True)
                with open(input_abs, 'wb') as out:
                    for chunk in client_file.chunks():
                        out.write(chunk)
                client_url = settings.MEDIA_URL + input_rel

                # Vista elegida
                # Vista elegida (forzamos a leer primero lo que llega por POST)
	raw_view = request.POST.get('view_number', '').strip()
	try:
    	chosen_view_num = int(raw_view) if raw_view else int(choose_view_form.cleaned_data['view_number'])
	except Exception:
   	 chosen_view_num = int(choose_view_form.cleaned_data['view_number'])

	# Log opcional para depurar (lo verás en Render > Logs)
	logger.info(f"[upload_photo] Vista seleccionada: {chosen_view_num}")

	chosen_abs = None
	for num, path in views_found:
   	 if num == chosen_view_num:
        	chosen_abs = path
        	break

                if not chosen_abs:
                    messages.error(request, 'No se encontró la vista seleccionada.')
                    return redirect('products:upload_photo')

                # Copia a media (para miniaturas) y guarda carpeta ORIGINAL para el .docx
                line_url, line_abs = copy_to_media_and_get_url(chosen_abs)
                if not line_abs:
                    messages.error(request, "No se pudo preparar la vista seleccionada.")
                    return redirect('products:upload_photo')

                request.session['work'] = {
                    'client_input_rel': input_rel,
                    'client_url': client_url,
                    'line_abs': line_abs,
                    'line_url': line_url,
                    'chosen_view_num': chosen_view_num,
                    'line_src_dir': str(Path(chosen_abs).parent),  # carpeta original (para .docx)
                }

                return redirect('products:result')

        else:
            upload_form = UploadPhotoForm()
            choose_view_form = ChooseViewForm(view_numbers=view_numbers)
            logo_form = LogoForm()

        # Crear miniaturas si hay vistas
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
    """
    Usa la API de imágenes con 'edit' (singular):
    - prompt: texto (del .docx de la vista)
    - image: la foto que subió el cliente
    Devuelve bytes de la imagen generada (base64).
    """
    with open(client_abs, "rb") as f:
        resp = client.images.edit(
            model="gpt-image-1",
            image=[f],               # imagen de entrada
            prompt=prompt_text,      # instrucciones
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
        selection = request.session.get('selection')
        work = request.session.get('work')
        if not selection or not work:
            messages.error(request, "Vuelve a iniciar la selección.")
            return redirect('products:select_category')

        ensure_dirs()

        client_rel = work['client_input_rel']
        client_abs = os.path.join(settings.MEDIA_ROOT, client_rel)
        chosen_view_num = work['chosen_view_num']

        # Carpeta ORIGINAL de la vista para leer el prompt .docx
        line_src_dir = work.get('line_src_dir')
        if not line_src_dir:
            messages.error(request, "No se encontró la carpeta de la vista para leer el prompt.")
            return redirect('products:upload_photo')

        prompt_text = load_prompt_for_view(Path(line_src_dir), chosen_view_num)

        # Llamada a OpenAI con la imagen subida y el prompt (.docx)
        result1_bytes = _call_openai_edit(
            client_abs=client_abs,
            prompt_text=prompt_text,
        )

        # Guardar imagen base
        result1_rel = f'uploads/output/Resultado_1_{uuid4()}.jpg'
        result1_abs = os.path.join(settings.MEDIA_ROOT, result1_rel)
        with open(result1_abs, 'wb') as f:
            f.write(result1_bytes)

        # --- Postpro: relieve/claridad ---
        post_rel = f'uploads/output/Resultado_1_post_{uuid4()}.jpg'
        post_abs = os.path.join(settings.MEDIA_ROOT, post_rel)
        enhance_mockup(result1_abs, post_abs)
        result1_url = settings.MEDIA_URL + post_rel
        final_url = result1_url
        # ---------------------------------

        # Limpiar sesión
        request.session.pop('work', None)
        request.session.pop('logo', None)

        return render(request, 'products/result.html', {
            'result1_url': result1_url,
            'final_url': final_url,
            'used_logo': False,
        })
    except Exception:
        logger.exception("Fallo inesperado en result_view")
        messages.error(request, "Ha ocurrido un error generando el resultado.")
        return redirect('products:upload_photo')
