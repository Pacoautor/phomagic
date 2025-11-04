import os
from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from PIL import Image
import io
import base64
from openai import OpenAI
from docx import Document

# Inicializar cliente OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def get_categories():
    """Lee las categorías desde media/lineas/"""
    lineas_path = os.path.join(settings.MEDIA_ROOT, 'lineas')
    if not os.path.exists(lineas_path):
        return []
    
    categories = []
    for item in os.listdir(lineas_path):
        item_path = os.path.join(lineas_path, item)
        if os.path.isdir(item_path):
            categories.append(item)
    return sorted(categories)

def get_subcategories(category):
    """Lee las subcategorías de una categoría"""
    category_path = os.path.join(settings.MEDIA_ROOT, 'lineas', category)
    if not os.path.exists(category_path):
        return []
    
    subcategories = []
    for item in os.listdir(category_path):
        item_path = os.path.join(category_path, item)
        if os.path.isdir(item_path):
            subcategories.append(item)
    return sorted(subcategories)

def get_views(category, subcategory):
    """Lee las vistas (PNG) de una subcategoría"""
    subcategory_path = os.path.join(settings.MEDIA_ROOT, 'lineas', category, subcategory)
    if not os.path.exists(subcategory_path):
        return []
    
    views = []
    files = os.listdir(subcategory_path)
    
    # Buscar archivos PNG
    png_files = [f for f in files if f.lower().endswith('.png')]
    
    for png_file in png_files:
        view_name = os.path.splitext(png_file)[0]
        view_data = {
            'name': view_name,
            'image': f'/media/lineas/{category}/{subcategory}/{png_file}',
            'png_file': png_file
        }
        views.append(view_data)
    
    return sorted(views, key=lambda x: x['name'])

def get_prompt(category, subcategory, view_name):
    """Lee el prompt desde el archivo DOCX correspondiente"""
    docx_path = os.path.join(
        settings.MEDIA_ROOT, 'lineas', category, subcategory, f'{view_name}.docx'
    )
    
    if not os.path.exists(docx_path):
        return "Genera una imagen profesional de producto."
    
    try:
        doc = Document(docx_path)
        prompt = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        return prompt.strip()
    except Exception as e:
        print(f"Error leyendo prompt: {e}")
        return "Genera una imagen profesional de producto."

def validate_image_quality(image_file):
    """Valida la calidad de la imagen subida"""
    try:
        image = Image.open(image_file)
        image_file.seek(0)  # Reset file pointer
        
        # Validar formato
        if image.format not in ['JPEG', 'PNG', 'JPG']:
            return False, "Formato no válido. Solo se aceptan JPG o PNG."
        
        # Validar tamaño mínimo (ej: 512x512)
        width, height = image.size
        if width < 512 or height < 512:
            return False, f"Imagen muy pequeña ({width}x{height}). Mínimo 512x512 píxeles."
        
        # Validar tamaño de archivo (max 10MB)
        image_file.seek(0, 2)  # Ir al final
        file_size = image_file.tell()
        image_file.seek(0)  # Reset
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            return False, "Archivo muy grande. Máximo 10MB."
        
        # Validación básica de nitidez usando varianza de Laplacian
        try:
            import numpy as np
            import cv2
            
            # Convertir a array
            img_array = np.array(image.convert('RGB'))
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Si la varianza es muy baja, probablemente esté desenfocada
            if laplacian_var < 100:
                return False, "Imagen desenfocada. Por favor, sube una imagen más nítida."
        except:
            # Si no está disponible OpenCV, continuar sin validación de nitidez
            pass
        
        # Validación de brillo promedio
        try:
            import numpy as np
            img_array = np.array(image.convert('L'))  # Convertir a escala de grises
            mean_brightness = np.mean(img_array)
            
            if mean_brightness < 30:
                return False, "Imagen muy oscura. Por favor, sube una imagen con mejor iluminación."
            if mean_brightness > 225:
                return False, "Imagen sobreexpuesta. Por favor, sube una imagen con mejor iluminación."
        except:
            # Si falla, continuar
            pass
        
        return True, "OK"
        
    except Exception as e:
        return False, f"Error al procesar la imagen: {str(e)}"

def select_category(request):
    """Vista principal: selección de categoría"""
    categories = get_categories()
    return render(request, "select_category.html", {"categories": categories})

def select_subcategory(request, category):
    """Vista de subcategorías"""
    subcategories = get_subcategories(category)
    return render(request, "select_subcategory.html", {
        "category": category,
        "subcategories": subcategories
    })

def view_products(request, category, subcategory):
    """Vista de vistas/productos"""
    views = get_views(category, subcategory)
    return render(request, "view_products.html", {
        "category": category,
        "subcategory": subcategory,
        "views": views
    })

def upload_photo(request, category, subcategory, view_name):
    """Vista de subida de foto y procesamiento con OpenAI"""
    
    if request.method == "POST" and request.FILES.get("photo"):
        photo = request.FILES["photo"]
        
        # Validar calidad de imagen
        is_valid, message = validate_image_quality(photo)
        
        if not is_valid:
            return render(request, "upload_photo.html", {
                "error": message,
                "category": category,
                "subcategory": subcategory,
                "view_name": view_name
            })
        
        # Obtener prompt
        prompt = get_prompt(category, subcategory, view_name)
        
        # Procesar con OpenAI
        try:
            # Convertir imagen a base64
            photo.seek(0)
            image_data = photo.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Llamar a OpenAI API
            response = client.images.edit(
                model="dall-e-2",
                image=image_data,
                prompt=prompt,
                n=1,
                size="1024x1024"
            )
            
            result_url = response.data[0].url
            
            return render(request, "upload_photo.html", {
                "success": True,
                "result_image": result_url,
                "category": category,
                "subcategory": subcategory,
                "view_name": view_name
            })
            
        except Exception as e:
            return render(request, "upload_photo.html", {
                "error": f"Error al procesar la imagen: {str(e)}",
                "category": category,
                "subcategory": subcategory,
                "view_name": view_name
            })
    
    return render(request, "upload_photo.html", {
        "category": category,
        "subcategory": subcategory,
        "view_name": view_name
    })
