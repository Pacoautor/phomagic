# catalog/views.py
import json, re
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

from .catalog_config import CATALOG, DEFAULTS
from .prompt_builder import build_prompts

HEX_RE = re.compile(r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")

def get_catalog(request):
    """
    Devuelve el catálogo mínimo + opciones por defecto para poblar la UI.
    """
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
    """
    Valida el payload de job y devuelve (ok, error_message, job_dict).
    Reutilizada por build_job y prepare_job para que sean consistentes.
    """
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
    """
    Valida la selección del cliente y devuelve un JOB JSON listo para el pipeline.
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

    return JsonResponse({"ok": True, "job": job},
                        json_dumps_params={"ensure_ascii": False, "indent": 2})

@csrf_exempt
def prepare_job(request):
    """
    Recibe el mismo JSON que /api/job/validate/ y devuelve:
    - job validado
    - view_tasks: lista de {view_id, prompt} por cada vista solicitada
    (No llama a OpenAI; solo construye prompts).
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

    view_tasks = build_prompts(job)
    return JsonResponse(
        {"ok": True, "job": job, "view_tasks": view_tasks},
        json_dumps_params={"ensure_ascii": False, "indent": 2}
    )
