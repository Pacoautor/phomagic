# catalog/generate_service.py
import io
import os
import time
from typing import List, Dict

import requests

from .prompt_builder import build_prompts


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

# Tamaños permitidos por gpt-image-1
def _closest_openai_size(w: int, h: int) -> str:
    return "1024x1536" if h >= w else "1536x1024"


def _download_image_bytes(url: str, max_retries: int = 3, backoff_sec: float = 1.5) -> bytes:
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
            ctype = r.headers.get("Content-Type", "")
            if not ctype.startswith(("image/", "application/octet-stream")):
                raise requests.HTTPError(f"Unexpected content-type: {ctype}", response=r)
            return r.content
        except Exception as e:
            last_exc = e
            if attempt < max_retries:
                time.sleep(backoff_sec * attempt)
                continue
            raise
    raise last_exc  # por si acaso


def _openai_generate(prompt: str, size: str) -> str:
    """
    Llama a /v1/images/generations → devuelve b64_json
    """
    url = f"{OPENAI_BASE_URL}/images/generations"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }
    json_payload = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "size": size,
    }
    r = requests.post(url, headers=headers, json=json_payload, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"OpenAI generate error {r.status_code}: {r.text}")
    data = r.json()
    return data["data"][0]["b64_json"]


def _openai_edit(image_bytes: bytes, prompt: str, size: str) -> str:
    """
    Llama a /v1/images/edits con multipart/form-data → devuelve b64_json
    """
    url = f"{OPENAI_BASE_URL}/images/edits"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }
    # files y data para multipart:
    files = {
        "image": ("input.jpg", image_bytes, "image/jpeg"),
    }
    data = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "size": size,
    }
    r = requests.post(url, headers=headers, files=files, data=data, timeout=180)
    if r.status_code >= 400:
        raise RuntimeError(f"OpenAI edit error {r.status_code}: {r.text}")
    j = r.json()
    return j["data"][0]["b64_json"]


def generate_views_from_job(job: Dict) -> List[Dict]:
    """
    Devuelve: [{ view_id, image_b64, model_size }]
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("Falta OPENAI_API_KEY en variables de entorno")

    opts = job["client_options"]
    size = opts["size_px"]
    target_size = _closest_openai_size(size["width"], size["height"])

    in_bytes = None
    if job["image"].get("image_url"):
        in_bytes = _download_image_bytes(job["image"]["image_url"])

    from .prompt_builder import build_prompts
    view_tasks = build_prompts(job)

    results = []
    for task in view_tasks:
        prompt = task["prompt"]
        if in_bytes:
            b64 = _openai_edit(in_bytes, prompt, target_size)
        else:
            b64 = _openai_generate(prompt, target_size)

        results.append({
            "view_id": task["view_id"],
            "image_b64": b64,
            "model_size": target_size,
        })

    return results
