# catalog/views.py
import json, re, os, uuid, io, base64
from typing import Tuple, Optional, Dict, List

from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import default_storage

from PIL import Image, ImageFilter, ImageStat

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


# ---------- Utilidades de guardado/post-proceso ----------

def _hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    s = hex_str.lstrip("#")
    if len(s) == 3:
        s = "".join(ch*2 for ch in s)
    return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))


def _parse_box(s: Optional[str]) -> Optional[Dict]:
    """
    Recibe un JSON como {"x":..,"y":..,"w":..,"h":..,"img_w":..,"img_h":..}
    """
    if not s:
        return None
    try:
        data = json.loads(s)
        for k in ["x", "y", "w", "h", "img_w", "img_h"]:
            if k not in data:
                return None
        if data["w"] <= 0 or data["h"] <= 0:
            return None
        return data
    except Exception:
        return None


def _save_b64_as_png_with_bg_and_resize(
    b64_str: str,
    bg_hex: str,
    target_w: int,
    target_h: int,
    prefix: str,
) -> Image.Image:
    """
    Decodifica base64 -> PIL.Image, compone sobre fondo HEX exacto,
    redimensiona a (target_w, target_h) y devuelve la PIL.Image resultante.
    """
    raw = base64.b64decode(b64_str)
    img = Image.open(io.BytesIO(raw))

    # Fondo exacto
    bg_rgb = _hex_to_rgb(bg_hex)
    canvas = Image.new("RGB", (img.width, img.height), bg_rgb)

    # Componer sobre fondo (respetando alfa)
    if img.mode in ("RGBA", "LA"):
        canvas.paste(img.convert("RGBA"), (0, 0), img.convert("RGBA"))
    else:
        canvas.paste(img.convert("RGB"), (0, 0))

    # Redimensionar al tamaño solicitado por el cliente
    if (canvas.width, canvas.height) != (target_w, target_h):
        canvas = canvas.resize((target_w, target_h), Image.LANCZOS)

    return canvas


def _match_color_to_region(src_rgb: Image.Image, dst_region_rgb: Image.Image) -> Image.Image:
    """
    Igualado simple de color por canal:
      gain_c = mean_dst_c / mean_src_c
      out_c = clamp(src_c * gain_c)
    """
    src = src_rgb.convert("RGB")
    dst = dst_region_rgb.convert("RGB")

    src_stat = ImageStat.Stat(src)
    dst_stat = ImageStat.Stat(dst)
    s_means = src_stat.mean  # [R,G,B]
    d_means = dst_stat.mean

    bands = src.split()
    adj_bands: List[Image.Image] = []
    for i, band in enumerate(bands):
        sm = max(1.0, s_means[i])
        dm = max(1.0, d_means[i])
        gain = dm / sm

        # tabla rápida de 0..255
        lut = [min(255, max(0, int(round(v * gain)))) for v in range(256)]
        adj_bands.append(band.point(lut))

    return Image.merge("RGB", tuple(adj_bands))


def _paste_with_feather(
    base_img: Image.Image,
    crop_rgb: Image.Image,
    xy: Tuple[int, int],
    feather: int = 4
):
    """
    Pega con máscara de borde suavizado (feather).
    """
    cw, ch = crop_rgb.size
    mask = Image.new("L", (cw, ch), 255)
    if feather > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=feather))
    base_img.paste(crop_rgb, xy, mask)


def _paste_original_regions(
    final_img: Image.Image,
    orig_rel_path: str,
    logo_box: Optional[Dict],
    neck_box: Optional[Dict],
    feather: int = 4,
    do_color_match: bool = True,
):
    """
    Pega los recortes EXACTOS del original (logo/etiqueta) sobre la imagen final,
    mapeando coordenadas de la imagen original -> tamaño final con:
    - igualado de color a la región destino
    - máscara feather para que no se note la junta
    """
    if not (logo_box or neck_box):
        return

    with default_storage.open(orig_rel_path, "rb") as fh:
        orig = Image.open(io.BytesIO(fh.read())).convert("RGB")
    orig_w, orig_h = orig.size

    sx = final_img.width / max(1, orig_w)
    sy = final_img.height / max(1, orig_h)

    def paste_box(b: Dict):
        x, y, w, h = b["x"], b["y"], b["w"], b["h"]
        crop = orig.crop((x, y, x + w, y + h))  # recorte original

        # Escalamos recorte al tamaño final correspondiente
        tw, th = max(1, int(round(w * sx))), max(1, int(round(h * sy)))
        crop_resized = crop.resize((tw, th), Image.LANCZOS)

        # Coordenadas destino en la imagen final
        xf, yf = int(round(x * sx)), int(round(y * sy))

        # Igualado de color al entorno destino (misma región del final)
        if do_color_match:
            # Recorta zona destino (limitando a los bordes)
            x2, y2 = min(final_img.width, xf + tw), min(final_img.height, yf + th)
            x1, y1 = max(0, xf), max(0, yf)
            if x2 > x1 and y2 > y1:
                dst_region = final_img.crop((x1, y1, x2, y2)).convert("RGB")
                # si el recorte sale de imagen, ajustamos también el source
                if (x1, y1) != (xf, yf) or (x2 - x1, y2 - y1) != (tw, th):
                    nx = 0 if x1 == xf else (xf - x1)
                    ny = 0 if y1 == yf else (yf - y1)
                    crop_resized = crop_resized.crop((nx, ny, nx + dst_region.width, ny + dst_region.height))
                crop_resized = _match_color_to_region(crop_resized, dst_region)

        # Pegar con feather
        _paste_with_feather(final_img, crop_resized, (xf, yf), feather=feather)

    if logo_box:
        paste_box(logo_box)
    if neck_box:
        paste_box(neck_box)


def _save_final_png(img: Image.Image, prefix: str) -> str:
    rel_path = os.path.join("outputs", f"{prefix}.png").replace("\\", "/")
    with io.BytesIO() as buf:
        img.save(buf, format="PNG")
        buf.seek(0)
        default_storage.save(rel_path, buf)
    return rel_path


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
    Genera imagen(es) por cada vista y guarda PNGs ya con fondo HEX exacto.
    Si se proporcionan logo_box_json / neck_box_json y orig_rel_path,
    repone esas zonas con el recorte original (con color match + feather).
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

    w = job["client_options"]["size_px"]["width"]
    h = job["client_options"]["size_px"]["height"]
    bg_hex = job["client_options"]["background"]["hex"]

    logo_box = _parse_box(job.get("logo_box_json"))
    neck_box = _parse_box(job.get("neck_box_json"))
    orig_rel = job.get("orig_rel_path")

    saved_results = []
    batch_id = uuid.uuid4().hex[:8]
    for r in results:
        prefix = f"{batch_id}_{r['view_id']}"
        composed = _save_b64_as_png_with_bg_and_resize(r["image_b64"], bg_hex, w, h, prefix)

        if orig_rel and (logo_box or neck_box):
            _paste_original_regions(composed, orig_rel, logo_box, neck_box, feather=5, do_color_match=True)

        rel_out = _save_final_png(composed, prefix)
        url = request.build_absolute_uri(settings.MEDIA_URL + rel_out)
        saved_results.append({
            "view_id": r["view_id"],
            "model_size": r["model_size"],
            "image_url": url,
        })

    return JsonResponse(
        {"ok": True, "job": job, "results": saved_results},
        json_dumps_params={"ensure_ascii": False, "indent": 2}
    )


@csrf_exempt
def upload_image(request):
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
# UI con marcado multi-zona (logo + etiqueta)
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
.card{max-width:980px;margin:auto;border:1px solid #e5e7eb;border-radius:12px;padding:20px}
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
a.dl{display:inline-block;margin-top:6px;font-size:12px}
.canvas-wrap{position:relative;display:inline-block;margin-top:12px}
#preview{max-width:100%;display:block}
#overlay{position:absolute;left:0;top:0}
.note{background:#fffbeb;border:1px solid #f59e0b;color:#92400e;padding:8px 10px;border-radius:8px;font-size:12px;margin-top:6px}
.modebar{display:flex;gap:8px;margin-top:8px}
.modebar .btn{background:#374151}
.modebar .btn.active{background:#111827}
.btn-outline{background:#fff;color:#111827;border:1px solid #d1d5db}
</style>
</head>
<body>
<div class="card">
  <h1>Generar vistas de catálogo</h1>

  <form id="formGen" action="/api/ui/generate/" method="post" enctype="multipart/form-data">
    <label>Imagen del producto (JPG/PNG/WebP)</label>
    <input id="fileInput" type="file" name="image" accept="image/*" required>

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
      <label class="badge"><input id="cbLogo" type="checkbox" name="logo"> Detectar/Respetar logo</label>
      <label class="badge"><input id="cbNeck" type="checkbox" name="neck_label"> Detectar etiqueta trasera</label>
    </div>

    <div class="note">Activa “logo” y/o “etiqueta”, elige el modo y dibuja un rectángulo en el preview. Puedes marcar <b>ambos</b>.</div>

    <div class="canvas-wrap" style="display:none" id="wrap">
      <img id="preview" alt="preview"/>
      <canvas id="overlay"></canvas>

      <div class="modebar" id="modebar" style="display:none">
        <button type="button" class="btn" id="btnModeLogo">Dibujar LOGO</button>
        <button type="button" class="btn" id="btnModeNeck">Dibujar ETIQUETA</button>
        <button type="button" class="btn btn-outline" id="btnClearLogo">Borrar LOGO</button>
        <button type="button" class="btn btn-outline" id="btnClearNeck">Borrar ETIQUETA</button>
      </div>
    </div>

    <input type="hidden" name="logo_box_json" id="logoBox">
    <input type="hidden" name="neck_box_json" id="neckBox">

    <div style="margin-top:12px">
      <button class="btn" type="submit">Generar</button>
    </div>
  </form>

  {RESULTS}
</div>

<script>
(function(){
  const fileInput = document.getElementById('fileInput');
  const wrap = document.getElementById('wrap');
  const img = document.getElementById('preview');
  const canvas = document.getElementById('overlay');
  const ctx = canvas.getContext('2d');
  const cbLogo = document.getElementById('cbLogo');
  const cbNeck = document.getElementById('cbNeck');
  const logoBoxInput = document.getElementById('logoBox');
  const neckBoxInput = document.getElementById('neckBox');

  const modebar = document.getElementById('modebar');
  const btnModeLogo = document.getElementById('btnModeLogo');
  const btnModeNeck = document.getElementById('btnModeNeck');
  const btnClearLogo = document.getElementById('btnClearLogo');
  const btnClearNeck = document.getElementById('btnClearNeck');

  let activeMode = null; // 'logo' | 'neck' | null
  let imgLoaded = false;
  let start = null;
  let boxLogo = null;
  let boxNeck = null;

  function fitCanvas(){
    canvas.width = img.clientWidth;
    canvas.height = img.clientHeight;
    canvas.style.width = img.clientWidth + 'px';
    canvas.style.height = img.clientHeight + 'px';
  }

  function draw(){
    ctx.clearRect(0,0,canvas.width,canvas.height);
    ctx.lineWidth = 2;

    if (boxLogo){
      ctx.strokeStyle = '#2563eb'; // azul
      ctx.strokeRect(boxLogo.x, boxLogo.y, boxLogo.w, boxLogo.h);
    }
    if (boxNeck){
      ctx.strokeStyle = '#16a34a'; // verde
      ctx.strokeRect(boxNeck.x, boxNeck.y, boxNeck.w, boxNeck.h);
    }
  }

  function relToNatural(b){
    const nx = Math.round(b.x * (img.naturalWidth / canvas.width));
    const ny = Math.round(b.y * (img.naturalHeight / canvas.height));
    const nw = Math.round(b.w * (img.naturalWidth / canvas.width));
    const nh = Math.round(b.h * (img.naturalHeight / canvas.height));
    return {x:nx,y:ny,w:nw,h:nh,img_w:img.naturalWidth,img_h:img.naturalHeight};
  }

  fileInput.addEventListener('change', e=>{
    const f = e.target.files[0];
    if(!f){ wrap.style.display='none'; return; }
    const url = URL.createObjectURL(f);
    img.src = url;
    img.onload = ()=>{
      imgLoaded = true;
      wrap.style.display='inline-block';
      fitCanvas();
      draw();
      updateModebar();
    };
  });

  window.addEventListener('resize', ()=>{
    if(!imgLoaded) return;
    fitCanvas();
    draw();
  });

  function updateModebar(){
    const any = cbLogo.checked || cbNeck.checked;
    modebar.style.display = any ? 'flex' : 'none';
    if (!any) { activeMode = null; }
    btnModeLogo.classList.toggle('active', activeMode==='logo');
    btnModeNeck.classList.toggle('active', activeMode==='neck');
  }

  cbLogo.addEventListener('change', ()=>{
    if (cbLogo.checked && !activeMode) activeMode = 'logo';
    if (!cbLogo.checked) { boxLogo = null; logoBoxInput.value=''; if (activeMode==='logo') activeMode=null; }
    updateModebar(); draw();
  });
  cbNeck.addEventListener('change', ()=>{
    if (cbNeck.checked && !activeMode) activeMode = 'neck';
    if (!cbNeck.checked) { boxNeck = null; neckBoxInput.value=''; if (activeMode==='neck') activeMode=null; }
    updateModebar(); draw();
  });

  btnModeLogo.addEventListener('click', ()=>{ if (cbLogo.checked){ activeMode='logo'; updateModebar(); }});
  btnModeNeck.addEventListener('click', ()=>{ if (cbNeck.checked){ activeMode='neck'; updateModebar(); }});
  btnClearLogo.addEventListener('click', ()=>{ boxLogo=null; logoBoxInput.value=''; draw(); });
  btnClearNeck.addEventListener('click', ()=>{ boxNeck=null; neckBoxInput.value=''; draw(); });

  canvas.addEventListener('mousedown', (e)=>{
    if(!activeMode || !imgLoaded) return;
    const rect = canvas.getBoundingClientRect();
    start = { x: e.clientX - rect.left, y: e.clientY - rect.top };
  });
  canvas.addEventListener('mousemove', (e)=>{
    if(!start) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left, y = e.clientY - rect.top;
    const b = { x: Math.min(start.x,x), y: Math.min(start.y,y), w: Math.abs(x-start.x), h: Math.abs(y-start.y) };
    if(activeMode==='logo') boxLogo = b; else boxNeck = b;
    draw();
  });
  canvas.addEventListener('mouseup', ()=>{
    if(!start) return; start=null;
    if(boxLogo){ logoBoxInput.value = JSON.stringify(relToNatural(boxLogo)); }
    if(boxNeck){ neckBoxInput.value = JSON.stringify(relToNatural(boxNeck)); }
  });
})();
</script>
</body>
</html>
"""

def _render_html(results_html: str = "") -> HttpResponse:
    return HttpResponse(HTML_PAGE.replace("{RESULTS}", results_html))

@csrf_exempt
def ui_upload_page(request):
    return _render_html("")


@csrf_exempt
def ui_generate_action(request):
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

    # Leer opciones
    category = request.POST.get("category", "Moda")
    subcategory = request.POST.get("subcategory", "Camisetas y Polos")
    size_str = request.POST.get("size", "1280x1920")
    try:
        w_str, h_str = size_str.lower().split("x")
        w, h = int(w_str), int(h_str)
    except Exception:
        w, h = 1280, 1920

    background_hex = (request.POST.get("background_hex", "#ffffff") or "#ffffff").strip()
    logo = "logo" in request.POST
    neck_label = "neck_label" in request.POST
    views_sel = request.POST.getlist("views") or ["estirada"]

    # Cajas (si se marcaron y se dibujaron)
    logo_box_json = request.POST.get("logo_box_json") if logo else None
    neck_box_json = request.POST.get("neck_box_json") if neck_label else None
    logo_box = _parse_box(logo_box_json)
    neck_box = _parse_box(neck_box_json)

    payload = {
        "category": category,
        "subcategory": subcategory,
        "views": views_sel,
        "options": {
            "size": {"width": w, "height": h},
            "background_hex": background_hex,
            "shadow": {
                "enabled": True,  # (el preset ya lo aplicamos en prompt/IA)
                "mode": "multiply", "opacity": 0.43, "angle": 90, "distance": 18, "spread": 0, "size": 21
            },
            "logo": logo,
            "neck_label": neck_label
        },
        "image_url": image_url,
        "orig_rel_path": rel_path,
        "logo_box_json": json.dumps(logo_box) if logo_box else None,
        "neck_box_json": json.dumps(neck_box) if neck_box else None,
    }

    ok, err, job = _validate_and_build_job(payload)
    if not ok:
        return _render_html(f"<p class='small'>Error: {err}</p>")

    try:
        results = generate_views_from_job(job)
    except Exception as e:
        return _render_html(f"<p class='small'>Fallo al generar: {e}</p>")

    batch_id = uuid.uuid4().hex[:8]
    tiles = []
    for r in results:
        prefix = f"{batch_id}_{r['view_id']}"
        composed = _save_b64_as_png_with_bg_and_resize(r["image_b64"], background_hex, w, h, prefix)

        if (logo_box or neck_box):
            _paste_original_regions(composed, rel_path, logo_box, neck_box, feather=5, do_color_match=True)

        rel_out = _save_final_png(composed, prefix)
        url_out = request.build_absolute_uri(settings.MEDIA_URL + rel_out)
        cap = f"Vista: {r['view_id']} · {w}x{h}"
        tiles.append(
            f"<figure><img src='{url_out}' alt='{cap}'><figcaption class='small'>{cap} · "
            f"<a class='dl' href='{url_out}' download>Descargar</a></figcaption></figure>"
        )

    grid = "<div class='imgbox'>" + "".join(tiles) + "</div>"
    msg = f"<p class='small'>Imagen subida: <a href='{image_url}' target='_blank'>{image_url}</a></p>"
    return _render_html(msg + grid)
