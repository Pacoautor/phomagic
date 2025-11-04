import os
import requests
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.contrib import messages

# Ruta base donde se guardarán temporalmente las imágenes subidas
UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, 'uploads')

def upload_photo(request, category=None, subcategory=None, view_name=None):
    """
    Permite al usuario subir una imagen, validarla, y enviarla a la API de OpenAI
    junto con el prompt correspondiente según la vista seleccionada.
    """
    context = {
        "category": category,
        "subcategory": subcategory,
        "view_name": view_name,
        "result_url": None
    }

    if request.method == "POST" and "photo" in request.FILES:
        photo = request.FILES["photo"]

        # Validación simple (extensión y tamaño)
        if not photo.name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            messages.error(request, "❌ Formato no permitido. Sube una imagen JPG, PNG o WEBP.")
            return render(request, "upload_photo.html", context)

        if photo.size > 5 * 1024 * 1024:  # 5 MB
            messages.error(request, "⚠️ La imagen supera los 5MB.")
            return render(request, "upload_photo.html", context)

        # Guardar imagen local temporalmente
        fs = FileSystemStorage(location=UPLOAD_DIR)
        filename = fs.save(photo.name, photo)
        local_path = os.path.join(UPLOAD_DIR, filename)

        # Crear prompt contextualizado
        prompt = f"Transforma esta imagen de la vista '{view_name}' en un diseño profesional para la categoría {category}/{subcategory}."

        # Llamada a la API de OpenAI
        try:
            with open(local_path, "rb") as img_file:
                response = requests.post(
                    "https://api.openai.com/v1/images/edits",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    files={"image": img_file},
                    data={"prompt": prompt, "size": "512x512"}
                )

            if response.status_code == 200:
                data = response.json()
                image_url = data["data"][0]["url"]
                context["result_url"] = image_url
            else:
                messages.error(request, "❌ Error en la API de OpenAI.")
        except Exception as e:
            messages.error(request, f"Error procesando la imagen: {e}")

    return render(request, "upload_photo.html", context)
