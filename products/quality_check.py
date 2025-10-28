# products/quality_check.py
from PIL import Image, ImageStat
import numpy as np

# Umbrales razonables para fotos de prendas
MIN_WIDTH = 800
MIN_HEIGHT = 800
BRIGHT_MIN = 40       # mínimo promedio (0–255)
BRIGHT_MAX = 220      # máximo promedio
CONTRAST_MIN = 35     # contraste mínimo (desviación típica)
SHARPNESS_MIN = 50    # nitidez mínima (varianza de Laplaciano)
CLIP_RATIO_MAX = 0.10 # % máximo de píxeles quemados/oscuros

def _to_gray_np(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("L"), dtype=np.float32)

def _laplacian_var(gray: np.ndarray) -> float:
    # Filtro Laplaciano 3x3
    K = np.array([[0,  1, 0],
                  [1, -4, 1],
                  [0,  1, 0]], dtype=np.float32)
    padded = np.pad(gray, 1, mode="reflect")
    out = np.zeros_like(gray)
    for i in range(gray.shape[0]):
        for j in range(gray.shape[1]):
            region = padded[i:i+3, j:j+3]
            out[i, j] = (region * K).sum()
    return float(out.var())

def _contrast_std(gray: np.ndarray) -> float:
    return float(gray.std())

def _brightness_mean(img: Image.Image) -> float:
    return float(ImageStat.Stat(img.convert("L")).mean[0])

def _clip_ratio(gray: np.ndarray) -> float:
    total = gray.size
    zeros = (gray <= 2).sum()
    highs = (gray >= 253).sum()
    return float((zeros + highs) / total)

def check_image_quality(abs_path: str):
    """
    Devuelve (ok: bool, razones: [str]).
    ok == True  → imagen apta
    ok == False → razones explica los fallos
    """
    reasons = []
    try:
        img = Image.open(abs_path).convert("RGB")
    except Exception:
        return False, ["No se pudo abrir la imagen. Sube un archivo JPG o PNG válido."]

    w, h = img.size
    if w < MIN_WIDTH or h < MIN_HEIGHT:
        reasons.append(f"Resolución insuficiente (mínimo {MIN_WIDTH}×{MIN_HEIGHT}px). Actual: {w}×{h}px.")

    bright = _brightness_mean(img)
    if not (BRIGHT_MIN <= bright <= BRIGHT_MAX):
        reasons.append(f"Iluminación deficiente (promedio {bright:.1f}/255). Usa luz natural o foco suave.")

    gray = _to_gray_np(img)
    contrast = _contrast_std(gray)
    if contrast < CONTRAST_MIN:
        reasons.append(f"Contraste muy bajo (σ={contrast:.1f}). La prenda se ve plana.")

    sharp = _laplacian_var(gray)
    if sharp < SHARPNESS_MIN:
        reasons.append(f"Imagen borrosa (nítidez {sharp:.1f}). Enfoca mejor la prenda.")

    clip = _clip_ratio(gray)
    if clip > CLIP_RATIO_MAX:
        reasons.append("Sobre/subexposición: demasiados píxeles quemados u oscuros.")

    return (len(reasons) == 0), reasons
