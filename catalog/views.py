# catalog/views.py
import json, re
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from .catalog_config import CATALOG, DEFAULTS

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

@csrf_exempt
def build_job(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("JSON inválido")

    category    = payload.get("category")
    subcategory = payload.get("subcategory")
    views_sel   = payload.get("views", [])
    options     = payload.get("options", {})
    image_url   = payload.get("image_url", None)
    upload_id   = payload.get("upload_id", None)

    if not category or not subcategory:
        return HttpResponseBadRequest("Falta category/subcategory")
    if category not in CATALOG or subcategory not in CATALOG[category]:
        return HttpResponseBadRequest("Category/Subcategory no válidas")

    valid_views = {v["id"] for v in CATALOG[category][subcategory]["views"]}
    if not views_sel or not set(views_sel).issubset(valid_views):
        return HttpResponseBadRequest(f"Vistas no válidas. Permitidas: {sorted(valid_views)}")

    sizes = CATALOG[category][subcategory]["sizes_px"]
    size = options.get("size") or {}
    w, h = size.get("width"), size.get("height")
    if not any((s["width"]==w and s["height"]==h) for s in sizes):
        return HttpResponseBadRequest(f"Tamaño no válido. Usa uno de: {sizes}")

    bg_hex = (options.get("background_hex") or DEFAULTS["background_hex"]).strip().upper()
    if not HEX_RE.match(bg_hex):
        return HttpResponseBadRequest("background_hex debe ser tipo #FFFFFF")

    shadow = options.get("shadow", DEFAULTS["shadow"])
    if not isinstance(shadow.get("enabled", True), bool):
        return HttpResponseBadRequest("shadow.enabled debe ser booleano")

    logo = bool(options.get("logo", DEFAULTS["logo"]))
    neck_label = bool(options.get("neck_label", DEFAULTS["neck_label"]))

    if not image_url and not upload_id:
        return HttpResponseBadRequest("Falta image_url o upload_id")

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

    return JsonResponse({"ok": True, "job": job}, json_dumps_params={"ensure_ascii": False, "indent": 2})
