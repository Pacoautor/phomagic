# products/views.py
import os
import io
from uuid import uuid4
from django.conf import settings
from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
from PIL import Image, ImageOps, ImageDraw
from .forms import SelectCategoryForm, UploadPhotoForm, ChooseViewForm, LogoForm
from django.contrib import messages

# === CONFIGURACIÓN: carpeta raíz de "fotos de línea" ===
# Coloca aquí tus carpetas "Categoria_Subcategoria" con 1.jpg, 2.jpg...
LINE_ROOT = os.path.join(os.path.dirname(__file__), 'lineas')

# === UTILIDADES ===
def ensure_dirs():
    os.makedirs(os.path.join(settings.MEDIA_ROOT, 'uploads', 'input'), exist_ok=True)
    os.makedirs(os.path.join(settings.MEDIA_ROOT, 'uploads', 'output'), exist_ok=True)

def list_line_thumbnails(category, subcategory):
    """
    Devuelve lista [(num, abs_path)] de vistas disponibles (1.jpg/png, 2.jpg/png, ...).
    Hace tolerante la búsqueda (ignora mayúsculas, acentos, paréntesis, etc.).
    """
    import unicodedata

    def normalize(s):
        s = s.lower().replace("(", "").replace(")", "").replace("[", "").replace("]", "")
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        return s.strip()

    normalized_target = normalize(f"{category}_{subcategory}")

    # Buscar carpeta coincidente dentro de 'lineas'
    for folder in os.listdir(LINE_ROOT):
        if normalize(folder) == normalized_target:
            folder_path = LINE_ROOT / folder
            break
    else:
        return []  # no coincide nada

    views = []
    for name in sorted(os.listdir(folder_path)):
        if name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            stem = os.path.splitext(name)[0]
            try:
                num = int(stem)
                views.append((num, str(folder_path / name)))
            except ValueError:
                continue
    views.sort(key=lambda t: t[0])
    return views

def copy_to_media_and_get_url(abs_path):
    """
    Copia una imagen de 'lineas' a MEDIA para poder servirla como <img src="..."> fácilmente.
    Devuelve (url, media_abs_path).
    """
    ensure_dirs()
    with open(abs_path, 'rb') as f:
        data = f.read()
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
    """
    Pega el logo redimensionándolo al rectángulo indicado.
    rect = (x, y, w, h) en píxeles sobre base_img.
    """
    x, y, w, h = rect
    logo = logo_img.convert('RGBA')
    logo = logo.resize((max(1, int(w)), max(1, int(h))), Image.LANCZOS)
    base_rgba = base_img.convert('RGBA')
    base_rgba.paste(logo, (int(x), int(y)), logo)
    return base_rgba.convert('RGB')

# ==========================================
#                VISTAS
# ==========================================

def select_category(request):
    """
    Paso 1: Selección de categoría, subcategoría, tamaño, color y si seguirá logotipo.
    """
    if request.method == 'POST':
        form = SelectCategoryForm(request.POST)
        if form.is_valid():
            request.session['selection'] = form.cleaned_data
            return redirect('products:upload_photo')
    else:
        form = SelectCategoryForm()

    return render(request, 'products/select_category.html', {
        'form': form,
    })

def upload_photo(request):
    """
    Paso 2: Subida de foto + listado de vistas (miniaturas por carpeta) + recuadro de logotipo opcional.
    """
    selection = request.session.get('selection')
    if not selection:
        return redirect('products:select_category')

    category = selection['category']
    subcategory = selection['subcategory']

    # Descubrir vistas disponibles:
    views_found = list_line_thumbnails(category, subcategory)
    view_numbers = [num for num, _ in views_found]

    if request.method == 'POST':
        upload_form = UploadPhotoForm(request.POST, request.FILES)
        choose_view_form = ChooseViewForm(request.POST, view_numbers=view_numbers)
        logo_form = LogoForm(request.POST, request.FILES)

        if upload_form.is_valid() and choose_view_form.is_valid():
            ensure_dirs()
            # Guardar foto del cliente en MEDIA
            client_file = upload_form.cleaned_data['client_photo']
            client_ext = os.path.splitext(client_file.name)[1].lower().lstrip('.')
            input_rel = f'uploads/input/{uuid4()}.{client_ext}'
            input_abs = os.path.join(settings.MEDIA_ROOT, input_rel)
            os.makedirs(os.path.dirname(input_abs), exist_ok=True)
            with open(input_abs, 'wb') as out:
                for chunk in client_file.chunks():
                    out.write(chunk)
            client_url = settings.MEDIA_URL + input_rel

            # Miniatura elegida (número)
            chosen_view_num = int(choose_view_form.cleaned_data['view_number'])
            # Encontrar ruta absoluta de la plantilla elegida
            chosen_abs = None
            for num, path in views_found:
                if num == chosen_view_num:
                    chosen_abs = path
                    break

            if not chosen_abs:
                messages.error(request, 'No se encontró la vista seleccionada.')
                return redirect('products:upload_photo')

            # Copiamos la “foto de línea” a MEDIA para servirla
            line_url, line_abs = copy_to_media_and_get_url(chosen_abs)

            # Guardamos en sesión lo necesario para llamar a la API
            request.session['work'] = {
                'client_input_rel': input_rel,
                'client_url': client_url,
                'line_abs': line_abs,
                'line_url': line_url,
                'chosen_view_num': chosen_view_num,
            }

            # Si el usuario marcó seguimiento de logotipo en el paso anterior, guardamos rect/archivo logo
            follow_logo = selection.get('follow_logo', False)
            if follow_logo:
                rx = logo_form.cleaned_data.get('rect_x')
                ry = logo_form.cleaned_data.get('rect_y')
                rw = logo_form.cleaned_data.get('rect_w')
                rh = logo_form.cleaned_data.get('rect_h')
                request.session['logo'] = {
                    'rect_x': rx, 'rect_y': ry, 'rect_w': rw, 'rect_h': rh
                }

                logo_file = logo_form.cleaned_data.get('logo_file')
                if logo_file:
                    logo_ext = os.path.splitext(logo_file.name)[1].lower().lstrip('.')
                    logo_rel = f'uploads/input/{uuid4()}.{logo_ext}'
                    logo_abs = os.path.join(settings.MEDIA_ROOT, logo_rel)
                    with open(logo_abs, 'wb') as out:
                        for chunk in logo_file.chunks():
                            out.write(chunk)
                    request.session['logo']['logo_rel'] = logo_rel

            return redirect('products:result')

    else:
        upload_form = UploadPhotoForm()
        choose_view_form = ChooseViewForm(view_numbers=view_numbers)
        logo_form = LogoForm()

    # Pasamos miniaturas como URLs servibles copiándolas a MEDIA temporal (solo para mostrar)
    thumbs = []
    for num, abs_path in views_found:
        url, _ = copy_to_media_and_get_url(abs_path)
        thumbs.append((num, url))

    return render(request, 'products/upload_photo.html', {
        'selection': selection,
        'upload_form': upload_form,
        'choose_view_form': choose_view_form,
        'logo_form': logo_form,
        'thumbnails': thumbs,
    })

def _call_openai_edit(client_abs, line_abs, background_hex, category, subcategory, chosen_view_num):
    """
    Simula/realiza la llamada a OpenAI para generar Resultado_1 con:
    - forma/disposición de la foto de línea N
    - textura de la foto del cliente
    - fondo dado
    Nota: Aquí utilizamos PIL como 'mock' para que el flujo no falle si no está la API;
    si tienes ya el código de OpenAI funcionando, reemplaza el bloque MOCK por tu llamada real.
    """
    # === MOCK con PIL (combina dos imágenes y pinta fondo) ===
    base = Image.open(line_abs).convert('RGB')
    client = Image.open(client_abs).convert('RGB')

    # Crear fondo del color pedido
    bg = Image.new('RGB', base.size, background_hex)
    # Hacemos un blend simple para simular textura
    client_resized = client.resize(base.size, Image.LANCZOS)
    simulated = Image.blend(bg, client_resized, alpha=0.35)
    out = Image.blend(simulated, base, alpha=0.65)

    out = add_white_border(out, border_px=50)
    buf = io.BytesIO()
    out.save(buf, format='JPEG', quality=95)
    return buf.getvalue()

def _call_openai_logo(result1_abs, logo_abs, rect_pixels):
    """
    Simula/realiza la segunda llamada: incrusta el logo dentro del rectángulo y elimina el marco rojo.
    Aquí igualmente usamos PIL como MOCK.
    """
    base = Image.open(result1_abs).convert('RGB')

    # El rectángulo viene en píxeles relativos a la imagen del cliente (sin borde).
    # Dado que result1 tiene borde blanco, aproximamos pegando al interior (con un pequeño margen).
    # Para una precisión exacta, ajusta según tu flujo real con la API.

    logo = Image.open(logo_abs).convert('RGBA')
    result = paste_logo_on_area(base, logo, rect_pixels)

    buf = io.BytesIO()
    result.save(buf, format='JPEG', quality=95)
    return buf.getvalue()

def result_view(request):
    """
    Paso 3: Lógica de generación (Resultado_1 y opcional Resultado final con logotipo) + render del resultado.
    """
    selection = request.session.get('selection')
    work = request.session.get('work')
    if not selection or not work:
        return redirect('products:select_category')

    ensure_dirs()

    # Datos base
    background_hex = selection['background']
    category = selection['category']
    subcategory = selection['subcategory']

    client_rel = work['client_input_rel']
    client_abs = os.path.join(settings.MEDIA_ROOT, client_rel)
    line_abs = work['line_abs']
    chosen_view_num = work['chosen_view_num']

    # === Primera "llamada" (Resultado_1) ===
    result1_bytes = _call_openai_edit(
        client_abs=client_abs,
        line_abs=line_abs,
        background_hex=background_hex,
        category=category,
        subcategory=subcategory,
        chosen_view_num=chosen_view_num,
    )
    result1_rel = f'uploads/output/Resultado_1_{uuid4()}.jpg'
    result1_abs = os.path.join(settings.MEDIA_ROOT, result1_rel)
    with open(result1_abs, 'wb') as f:
        f.write(result1_bytes)
    result1_url = settings.MEDIA_URL + result1_rel

    final_rel = result1_rel  # por defecto
    final_url = result1_url

    # === Si hay seguimiento de logotipo, segunda "llamada" ===
    if selection.get('follow_logo'):
        logo_info = request.session.get('logo', {})
        rx = logo_info.get('rect_x')
        ry = logo_info.get('rect_y')
        rw = logo_info.get('rect_w')
        rh = logo_info.get('rect_h')
        logo_rel = logo_info.get('logo_rel')

        if all(v is not None for v in (rx, ry, rw, rh)) and logo_rel:
            # Convertimos % a píxeles relativos al tamaño de Resultado_1 (quitando borde estimado de 50 px que agregamos)
            img = Image.open(result1_abs)
            W, H = img.size
            # Quitamos borde de 50 px para aproximar al área útil
            content_x0, content_y0 = 50, 50
            content_w, content_h = W - 100, H - 100

            px = content_x0 + int((rx / 100.0) * content_w)
            py = content_y0 + int((ry / 100.0) * content_h)
            pw = int((rw / 100.0) * content_w)
            ph = int((rh / 100.0) * content_h)

            logo_abs = os.path.join(settings.MEDIA_ROOT, logo_rel)

            final_bytes = _call_openai_logo(
                result1_abs=result1_abs,
                logo_abs=logo_abs,
                rect_pixels=(px, py, pw, ph)
            )
            final_rel = f'uploads/output/Resultado_final_{uuid4()}.jpg'
            final_abs = os.path.join(settings.MEDIA_ROOT, final_rel)
            with open(final_abs, 'wb') as f:
                f.write(final_bytes)
            final_url = settings.MEDIA_URL + final_rel

    # Limpiamos sesión “transitoria” pero dejamos selection para posible "volver a empezar"
    request.session.pop('work', None)
    request.session.pop('logo', None)

    return render(request, 'products/result.html', {
        'result1_url': result1_url,
        'final_url': final_url,
        'used_logo': selection.get('follow_logo', False),
    })
