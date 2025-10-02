# catalog/generate_service.py

import base64
import io
import requests
from typing import List, Dict
from .prompt_builder import build_prompts
from .openai_client import get_client

# Tamaños permitidos por gpt-image-1 (docs): 1024x1024, 1024x1536, 1536x1024.
# Nosotros convertimos el tamaño pedido (ej. 1280x1920) al más cercano soportado
# manteniendo la orientación (vertical).
def _closest_openai_size(w: int, h: int) -> str:
    portrait = h >= w
    if portrait:
        # 1024x1536 es el vertical permitido
        return "1024x1536"
    else:
        return "1536x1024"  # horizontal

def _download_image_bytes(url: str) -> bytes:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content

def generate_views_from_job(job: Dict) -> List[Dict]:
    """
    Recibe el JOB ya validado (misma estructura que /api/job/validate)
    y devuelve una lista de resultados por vista:
    [{ view_id, image_b64 }]
    """
    opts = job["client_options"]
    size = opts["size_px"]
    target_size = _closest_openai_size(size["width"], size["height"])

    # Descarga la imagen de entrada si viene por URL
    in_bytes = None
    if job["image"].get("image_url"):
        in_bytes = _download_image_bytes(job["image"]["image_url"])
    # (Si usas upload_id propio, aquí deberías recuperar los bytes desde tu storage)

    view_tasks = build_prompts(job)

    client = get_client()
    results = []

    for task in view_tasks:
        prompt = task["prompt"]

        if in_bytes:
            # Edición con imagen base (image editing)
            # Docs: images.edits con gpt-image-1 (modelo de edición). :contentReference[oaicite:1]{index=1}
            with io.BytesIO(in_bytes) as f:
                f.name = "input.jpg"  # algunos bindings esperan un .name
                resp = client.images.edits(
                    model="gpt-image-1",
                    image=f,             # imagen base
                    prompt=prompt,       # instrucciones (vista)
                    size=target_size,    # tamaño soportado por el modelo
                    # n=1 por defecto (una imagen por vista)
                )
        else:
            # Generación pura (por si no hubiera imagen base)
            # Docs: images.generate con gpt-image-1. :contentReference[oaicite:2]{index=2}
            resp = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size=target_size,
            )

        # El SDK v1 retorna base64 en data[0].b64_json
        b64 = resp.data[0].b64_json
        results.append({
            "view_id": task["view_id"],
            "image_b64": b64,
            "model_size": target_size,
        })

    return results
