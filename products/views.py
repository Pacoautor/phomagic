
import os
import base64
from django.shortcuts import render, redirect
from django.contrib import messages
from PIL import Image, ImageEnhance, ImageFilter
from openai import OpenAI
from .quality_check import check_image_quality  # ✅ Import del validador de calidad

# === LLAMADA A OPENAI: images.edit (prompt + imagen del cliente) ===
def _call_openai_edit(client_abs, prompt_text):
    """
    Usa la API de imágenes (images.edit) para enviar:
    - prompt: texto (del .docx de la vista)
    - image: la foto que subió el cliente
    Devuelve bytes de la imagen generada.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    with open(client_abs, "rb") as f:
        response = client.images.edit(
            model="gpt-image-1",
            image=f,
            prompt=prompt_text,
            size="1024x1024",
        )

    result_b64 = response.data[0].b64_json
    return base64.b64decode(result_b64)


# === POSTPROCESADO: realce y claridad ===
def enhance_mockup(abs_path_in, abs_path_out):
    """
    Postpro ligero para dar más relieve y claridad al tejido.
    - Micro-contraste (UnsharpMask)
    - Contraste global
    - Nitidez general
    - Corrección gamma (~1.30 equivalente a Photoshop)
    """
    img = Image.open(abs_path_in).convert('RGB')
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))
    img = ImageEnhance.Contrast(img).enhance(1.06)
    img = ImageEnhance.Sharpness(img).enhance(1.08)

    # ✅ Ajuste de gamma 1.30
    gamma = 1.30
    lut = [pow(x / 255., 1 / gamma) * 255 for x in range(256)]
    lut = lut * 3
    img = img.point(lut)

    img.save(abs_path_out, quality=95)


# === FUNCIÓN PRINCIPAL DE RESULTADO ===
def result_view(request):
    try:
        # Recuperar ruta de imagen subida
        client_rel = request.session.get("client_image")
        if not client_rel:
            messages.error(request, "No se encontró la imagen del cliente.")
            return redirect("products:upload_photo")

        client_abs = os.path.join("media", client_rel)

        # Recuperar prompt según vista elegida
        prompt_text = request.session.get("prompt_text")
        if not prompt_text:
            messages.error(request, "No se encontró el texto de instrucciones.")
            return redirect("products:upload_photo")

        # === VALIDACIÓN DE CALIDAD (ANTES DE LLAMAR A OPENAI) ===
        ok, reasons = check_image_quality(client_abs)
        if not ok:
            msg = "⚠️ La imagen no cumple los requisitos de calidad:\n- " + "\n- ".join(reasons)
            messages.error(request, msg)
            return redirect('products:upload_photo')
        # =========================================================

        # Llamada a la API de OpenAI
        result1_bytes = _call_openai_edit(
            client_abs=client_abs,
            prompt_text=prompt_text,
        )

        # Guardar resultado temporal
        result_abs = os.path.join("media", "uploads", "result", "result1.jpg")
        with open(result_abs, "wb") as f:
            f.write(result1_bytes)

        # Realzar y guardar resultado final
        enhance_mockup(result_abs, result_abs)

        return render(request, "products/result.html", {"result_image": result_abs})

    except Exception as e:
        print(f"Fallo inesperado en result_view: {e}")
        messages.error(request, "Ocurrió un error al generar la imagen.")
        return redirect("products:upload_photo")
