# catalog/generate_service.py

import io
import time
from typing import List, Dict

import requests

from .prompt_builder import build_prompts
from .openai_client import get_client


# Tamaños permitidos por gpt-image-1: 1024x1024, 1024x1536 (vertical), 1536x1024 (horizontal).
def _closest_openai_size(w: int, h: int) -> str:
    return "1024x1536" if h >= w else "1536x1024"


def _download_image_bytes(url: str, max_retries: int = 3, backoff_sec: float = 1.5) -> bytes:
    """
    Descarga con cabeceras y reintentos (maneja 429/403/5xx).
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
            r.raise_for_status()
            # A veces devuelven HTML con 200; comprobamos content-type
            ctype = r.headers.get("Content-Type", "")
            if not ctype.startswith(("image/", "application/octet-stream")):
                raise requests.HTTPError(f"Unexpected content-type: {ctype}", response=r)
            return r.content
        except Exception as e:
            if attempt < max_retries:
                time.sleep(backoff_sec * attempt)
                last_exc = e
                continue
            raise
    if last_exc:
        raise last_exc


def generate_views_from_job(job: Dict) -> List[Dict]:
    """
    Devuelve: [{ view_id, image_b64, model_size }]
    """
    opts = job["client_options"]
    size = opts["size_px"]
    target_size = _closest_openai_size(size["width"], size["height"])

    # Descarga imagen base si viene por URL
    in_bytes = None
    if job["image"].get("image_url"):
        in_bytes = _download_image_bytes(job["image"]["image_url"])

    view_tasks = build_prompts(job)
    client = get_client()
    results = []

    for task in view_tasks:
        prompt = task["prompt"]

        if in_bytes:
            # **Edición** con imagen base usando images.generate (SDK v1.x)
            with io.BytesIO(in_bytes) as f:
                f.name = "input.jpg"  # algunos bindings leen .name
                resp = client.images.generate(
                    model="gpt-image-1",
                    prompt=prompt,
                    size=target_size,
                    image=f,  # ← imagen base
                )
        else:
            # Generación pura (sin imagen base)
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
