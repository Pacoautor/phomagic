from PIL import Image

def validate_image_quality(uploaded_file):
    """Valida formato, tamaño y resolución mínima de una imagen."""

    try:
        img = Image.open(uploaded_file)

        # 🔹 Validar formato
        if img.format not in ['JPEG', 'PNG', 'WEBP']:
            return False, "Formato no válido. Usa JPG, PNG o WEBP."

        # 🔹 Validar resolución mínima
        if img.width < 512 or img.height < 512:
            return False, "La imagen debe tener al menos 512x512 píxeles."

        # 🔹 Validar tamaño máximo (5 MB)
        uploaded_file.seek(0, 2)
        size_mb = uploaded_file.tell() / (1024 * 1024)
        uploaded_file.seek(0)
        if size_mb > 5:
            return False, "La imagen supera el tamaño máximo permitido (5 MB)."

        return True, None

    except Exception:
        return False, "El archivo subido no es una imagen válida."
