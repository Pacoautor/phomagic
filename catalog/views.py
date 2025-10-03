# catalog/views.py
import json, re, os, uuid, io, base64
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import default_storage

from .catalog_config import CATALOG, DEFAULTS
from .prompt_builder import build_prompts
from .generate_service import generate_views_from_job

HEX_RE = re.compile(r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")

def get_catalog(request):
    data = {
        "catalog": CATALOG,
        "defaults": DEFAULTS,
        "notes": {
            "color_input": "Acepta códigos HEX (#ffffff) estilo Photoshop.",
            "shadow": "Preset tipo Photoshop (Multiplicar, 43%, 90°, 18px, 0%, 21px).",
        }
    }
    return JsonResponse(data, json_dumps_params={"ensure_ascii": False})

def _validate_and_build_job(payload: dict):
    category    = payload.get("category")
    subcategory = payload.get("subcategory")
    views_sel   = payload.get("views", [])
    options     = payload.get("options", {})
    image_url   = payload.get("image_url", None)
    upload_id   = payload.get("upload_id", None)

    if not category or not subcategory:
        return False, "Falta category/subcategory", None
    if category not in CATALOG or subcategory not in CATALOG[category]:
        return False, "Category/Subcategory no válidas", None

    valid_views = {v["id"] for v in CATALOG[category][subcategory]["views"]}
    if not views_sel or not set(views_sel).issubset(valid_views):
        return False, f"Vistas no válidas. Permitidas: {sorted(valid_views)}", None

    sizes = CATALOG[category][subcategory]["sizes_px"]
    size = options.get("size") or {}
    w, h = size.get("width"), size.get("height")
    if not any((s["width"] == w and s["height"] == h) for s in sizes):
        return False, f"Tamaño no válido. Usa uno de: {sizes}", None

    bg_hex = (options.get("background_hex") or DEFAULTS["background_hex"]).strip().upper()
    if not HEX_RE.match(bg_hex):
        return False, "background_hex debe ser tipo #FFFFFF", None

    shadow = options.get("shadow", DEFAULTS["shadow"])
    if not isinstance(shadow.get("enabled", True), bool):
        return False, "shadow.enabled debe ser booleano", None

    logo = bool(options.get("logo", DEFAULTS["logo"]))
    neck_label = bool(options.get("neck_label", DEFAULTS["neck_label"]))

    if not image_url and not upload_id:
        return False, "Falta image_url o upload_id", None

    job = {
        "category": category,
        "subcategory": subcategory,
        "image": {"image_url": image_url, "upload_id": upload_id},
        "client_options": {
            "size_px": {"width": w, "height": h},
            "background": {"hex": bg_hex},
            "shadow": shadow,
            "logo": logo,
            "neck_label": neck_label
        },
        "views_requested": [{"id": vid} for vid in views_sel]
    }
    return True, None, job

@csrf_exempt
def build_job(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("JSON inválido")

    ok, err, job = _validate_and_build_job(payload)
    if not ok:
        return HttpResponseBadRequest(err)

    return JsonResponse({"ok": True, "job": job},
                        json_dumps_params={"ensure_ascii": False, "indent": 2})

@csrf_exempt
def prepare_job(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("JSON inválido")

    ok, err, job = _validate_and_build_job(payload)
    if not ok:
        return HttpResponseBadRequest(err)

    view_tasks = build_prompts(job)
    return JsonResponse(
        {"ok": True, "job": job, "view_tasks": view_tasks},
        json_dumps_params={"ensure_ascii": False, "indent": 2}
    )

@csrf_exempt
def generate_job(request):
    """
    Genera imagen(es) por cada vista usando OpenAI gpt-image-1.
    Devuelve: { ok, job, results: [ {view_id, image_b64, model_size} ] }
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("JSON inválido")

    ok, err, job = _validate_and_build_job(payload)
    if not ok:
        return HttpResponseBadRequest(err)

    try:
        results = generate_views_from_job(job)
    except Exception as e:
        return HttpResponseBadRequest(f"Fallo al generar imágenes: {e}")

    return JsonResponse(
        {"ok": True, "job": job, "results": results},
        json_dumps_params={"ensure_ascii": False, "indent": 2}
    )

@csrf_exempt
def upload_image(request):
    """
    Sube una imagen (multipart/form-data, campo 'image') y devuelve su URL pública.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST only (multipart/form-data)")

    f = request.FILES.get("image")
    if not f:
        return HttpResponseBadRequest("Falta el campo 'image' en el formulario")

    ext = os.path.splitext(f.name)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"

    fname = f"{uuid.uuid4().hex}{ext}"
    rel_path = os.path.join("uploads", fname).replace("\\", "/")

    saved_path = default_storage.save(rel_path, f)
    file_url = request.build_absolute_uri(settings.MEDIA_URL + saved_path)

    return JsonResponse({"ok": True, "url": file_url},
                        json_dumps_params={"ensure_ascii": False, "indent": 2})

# =========================
# UI sencilla (sin templates)
# =========================

HTML_PAGE = """
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Sube tu foto • Phomagic</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:24px;line-height:1.4}
.card{max-width:780px;margin:auto;border:1px solid #e5e7eb;border-radius:12px;padding:20px}
h1{font-size:22px;margin:0 0 12px}
label{display:block;margin:8px 0 4px;font-weight:600}
input[type=file],select,input[type=text]{width:100%;padding:8px;border:1px solid #d1d5db;border-radius:8px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.btn{background:#111827;color:#fff;border:none;padding:10px 16px;border-radius:8px;cursor:pointer}
.badge{display:inline-block;background:#f3f4f6;border:1px solid #e5e7eb;padding:6px 8px;border-radius:999px;margin-right:8px}
.imgbox{display:grid;grid-template-columns:repeat(auto-fill, minmax(220px,1fr));gap:12px;margin-top:16px}
img{max-width:100%;border-radius:8px;border:1px solid #e5e7eb}
.small{color:#6b7280;font-size:12px}
</style>
</head>
<body>
<div class="card">
  <h1>Generar vistas de catálogo</h1>
  <form action="/api/ui/generate/" method="post" enctype="multipart/form-data">
    <label>Imagen del producto (JPG/PNG/WebP)</label>
    <input type="file" name="image" required>

    <div class="grid">
      <div>
        <label>Categoría</label>
        <select name="category">
          <option value="Moda">Moda</option>
        </select>
      </div>
      <div>
        <label>Subcategoría</label>
        <select name="subcategory">
          <option value="Camisetas y Polos">Camisetas y Polos</option>
        </select>
      </div>
    </div>

    <label>Vistas</label>
    <div class="row">
      <label class="badge"><input type="checkbox" name="views" value="estirada" checked> Estirada</label>
      <label class="badge"><input type="checkbox" name="views" value="plegada"> Plegada</label>
      <label class="badge"><input type="checkbox" name="views" value="maniqui_invisible"> Maniquí invisible</label>
    </div>

    <div class="grid">
      <div>
        <label>Tamaño</label>
        <select name="size">
          <option value="1280x1920" selected>1280x1920</option>
          <option value="720x800">720x800</option>
          <option value="420x540">420x540</option>
        </select>
      </div>
      <div>
        <label>Fondo (HEX)</label>
        <input type="text" name="background_hex" value="#ffffff">
        <div class="small">Formato Photoshop (ej. #FFFFFF)</div>
      </div>
    </div>

    <label>Sombra</label>
    <div class="row">
      <label class="badge"><input type="checkbox" name="shadow_enabled" checked> Activar sombra</label>
      <span class="small">Preset: Multiplicar, 43%, 90°, 18px, 0%, 21px</span>
    </div>

    <div class="row">
      <label class="badge"><input type="checkbox" name="logo" checked> Detectar/Respetar logo</label>
      <label class="badge"><input type="checkbox" name="neck_label"> Detectar etiqueta trasera</label>
    </div>

    <div style="margin-top:12px">
      <button class="btn" type="submit">Generar</button>
    </div>
  </form>

  {RESULTS}
</div>
</body>
</html>
"""

def _render_html(results_html: str = "") -> HttpResponse:
    return HttpResponse(HTML_PAGE.replace("{RESULTS}", results_html))

@csrf_exempt
def ui_upload_page(request):
    # Solo muestra el formulario
    return _render_html("")

@csrf_exempt
def ui_generate_action(request):
    """
    Maneja el formulario: sube imagen -> construye job -> genera vistas -> muestra resultados.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")

    f = request.FILES.get("image")
    if not f:
        return _render_html("<p class='small'>Falta la imagen.</p>")

    # Guardar imagen subida
    ext = os.path.splitext(f.name)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    fname = f"{uuid.uuid4().hex}{ext}"
    rel_path = os.path.join("uploads", fname).replace("\\", "/")
    saved_path = default_storage.save(rel_path, f)
    image_url = request.build_absolute_uri(settings.MEDIA_URL + saved_path)

    # Leer campos
    category = request.POST.get("category", "Moda")
    subcategory = request.POST.get("subcategory", "Camisetas y Polos")
    size_str = request.POST.get("size", "1280x1920")
    try:
        w_str, h_str = size_str.lower().split("x")
        w, h = int(w_str), int(h_str)
    except Exception:
        w, h = 1280, 1920

    background_hex = (request.POST.get("background_hex", "#ffffff") or "#ffffff").strip()
    shadow_enabled = "shadow_enabled" in request.POST
    logo = "logo" in request.POST
    neck_label = "neck_label" in request.POST

    # Vistas marcadas
    views_sel = request.POST.getlist("views")
    if not views_sel:
        views_sel = ["estirada"]

    # Construir payload idéntico al de la API
    payload = {
        "category": category,
        "subcategory": subcategory,
        "views": views_sel,
        "options": {
            "size": {"width": w, "height": h},
            "background_hex": background_hex,
            "shadow": {
                "enabled": shadow_enabled,
                "mode": "multiply",
                "opacity": 0.43,
                "angle": 90,
                "distance": 18,
                "spread": 0,
                "size": 21
            },
            "logo": logo,
            "neck_label": neck_label
        },
        "image_url": image_url
    }

    # Validar y generar
    ok, err, job = _validate_and_build_job(payload)
    if not ok:
        return _render_html(f"<p class='small'>Error: {err}</p>")

    try:
        results = generate_views_from_job(job)
    except Exception as e:
        return _render_html(f"<p class='small'>Fallo al generar: {e}</p>")

    # Renderizar resultados en HTML (img base64)
    imgs = []
    for r in results:
        src = f"data:image/png;base64,{r['image_b64']}"
        cap = f"Vista: {r['view_id']} · {r['model_size']}"
        imgs.append(f"<figure><img src='{src}' alt='{cap}'><figcaption class='small'>{cap}</figcaption></figure>")
    grid = "<div class='imgbox'>" + "".join(imgs) + "</div>"

    msg = f"<p class='small'>Imagen subida: <a href='{image_url}' target='_blank'>{image_url}</a></p>"
    return _render_html(msg + grid)

