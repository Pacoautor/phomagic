from PIL import Image

def validate_image_quality(image):
    img = Image.open(image)
    width, height = img.size
    if width < 512 or height < 512:
        return False, f"La imagen es demasiado pequeña ({width}x{height}). Mínimo: 512x512"
    if image.size > 5 * 1024 * 1024:
        return False, "El tamaño máximo permitido es de 5MB"
    return True, "OK"
