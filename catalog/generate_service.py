# catalog/generate_service.py

import base64
import io
import time
from typing import List, Dict

import requests

from .prompt_builder import build_prompts
from .openai_client import get_client


# Tamaños permitidos por gpt-image-1: 1024x1024, 1024x1536 (vertical), 1536x1024 (horizontal).
def _closest_openai_size(w: int, h: int) -> str:
    portrait = h >= w
    return "1024x1536" if portrait else "1536x1024"


def _download_image_bytes(url: str, max_retries: int = 3, backoff_sec: float = 1.5) -> bytes:
    """
    Descarga una imagen con cabeceras 'amigables' y reintentos (maneja 429/403/5xx).
    Lanza requests.HTTPError si no lo consigue.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PhomagicBot/1.0; +https://www.phomagic.com)",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": "https://www.phomagic.com/",
    }
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=30)
            # En algunos hosts, 200 con HTML de error: comprobamos content-type
            ctype = r.headers.get("Content-Type", "")
            if r.status_code == 200 and not ctype.startswith(("image/", "application/octet-stream")):
                # Si es HTML, lo tratamos como error para forzar retry
                r.raise_for_status()
            r.raise_for_status()
            return r.content
        except requests.HTTPError as e:
            # Reintenta en 429/5xx o 403 puntuales
            status = getattr(e.response, "status_code", None)
            if status in (429, 500, 502, 503, 504, 403) and attempt < max_retries:
                time.sleep(backoff_sec * attempt)
                last_exc = e
                continue
            raise
        except Exception as e:
            # Errores de red/transitorios: reintentar
            if attempt < max_retries:
                time.sleep(backoff_sec * attempt)
                last_exc = e
                continue
            raise
    # Si llegamos aquí (muy raro), relanzamos el último error
    if last_exc:
        raise last_exc


def generate_views_from_job(job: Dict) -> List[Dict]:
    """
    Recibe el JOB ya validado y devuelve resultados por vista:
    [{ view_id, image_b64, model_size }]
    """
    opts = job["client_options"]
    size = opts["size_px"]
    target_size = _closest_openai_size(size["width"], size["height"])

    # Descarga la imagen de entrada si viene por URL
    in_bytes = None
    if job["image"].get("image_url"):
        in_bytes = _download_image_bytes(job["image"]["image_url"])
    # (Si usas upload_id propio, aquí recupera bytes desde tu storage)

    view_tasks = build_prompts(job)
    client = get_client()
    results = []

    for task in view_tasks:
        prompt = task["prompt"]

        if in_bytes:
            # Edición con imagen base
            with io.BytesIO(in_bytes) as f:
                f.name = "input.jpg"
                resp = client.images.edits(
                    model="gpt-image-1",
                    image=f,
                    prompt=prompt,
                    size=target_size,
                )
        else:
            # Generación sin imagen base (fallback)
            resp = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size=target_size,
            )

        b64 = resp.data[0].b64_json
        results.append({
            "view_id": task["view_id"],
            "image_b64": b64,
            "model_size": target_size,
        })

    return results
