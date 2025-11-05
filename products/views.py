import os
from django.shortcuts import render
from django.conf import settings
from pathlib import Path

def get_categories():
    lineas_path = Path(settings.MEDIA_ROOT) / 'lineas'
    if not lineas_path.exists():
        return []
    return sorted([d.name for d in lineas_path.iterdir() if d.is_dir()])

def get_subcategories(category):
    category_path = Path(settings.MEDIA_ROOT) / 'lineas' / category
    if not category_path.exists():
        return []
    return sorted([d.name for d in category_path.iterdir() if d.is_dir()])

def get_views(category, subcategory):
    subcategory_path = Path(settings.MEDIA_ROOT) / 'lineas' / category / subcategory
    if not subcategory_path.exists():
        return []
    
    views = []
    png_files = list(subcategory_path.glob('*.png'))
    
    for png_file in png_files:
        view_name = png_file.stem
        views.append({
            'name': view_name,
            'image': f'/media/lineas/{category}/{subcategory}/{png_file.name}',
        })
    
    return sorted(views, key=lambda x: x['name'])

def get_prompt(category, subcategory, view_name):
    try:
        from docx import Document
        docx_path = Path(settings.MEDIA_ROOT) / 'lineas' / category / subcategory / f'{view_name}.docx'
        
        if not docx_path.exists():
            return "Genera una imagen profesional de producto."
        
        doc = Document(str(docx_path))
        prompt = '\n'.join([p.text for p in doc.paragraphs if p.text.strip()])
        return prompt if prompt else "Genera una imagen profesional de producto."
    except:
        return "Genera una imagen profesional de producto."

def select_category(request):
    categories = get_categories()
    return render(request, "select_category.html", {"categories": categories})

def select_subcategory(request, category):
    subcategories = get_subcategories(category)
    return render(request, "select_subcategory.html", {
        "category": category,
        "subcategories": subcategories
    })

def view_products(request, category, subcategory):
    views = get_views(category, subcategory)
    return render(request, "view_products.html", {
        "category": category,
        "subcategory": subcategory,
        "views": views
    })

def upload_photo(request, category, subcategory, view_name):
    if request.method == "POST" and request.FILES.get("photo"):
        photo = request.FILES["photo"]
        
        if not photo.name.lower().endswith((".jpg", ".jpeg", ".png")):
            return render(request, "upload_photo.html", {
                "error": "Formato no válido. Sube JPG o PNG.",
                "category": category,
                "subcategory": subcategory,
                "view_name": view_name
            })
        
        try:
            from openai import OpenAI
            
            # Intentar múltiples formas de obtener la API key
            api_key = None
            
            # Método 1: os.environ directo
            if 'OPENAI_API_KEY' in os.environ:
                api_key = os.environ['OPENAI_API_KEY']
                print(f"Método 1 (os.environ): {api_key[:20] if api_key else 'None'}...")
            
            # Método 2: os.getenv
            if not api_key:
                api_key = os.getenv('OPENAI_API_KEY')
                print(f"Método 2 (os.getenv): {api_key[:20] if api_key else 'None'}...")
            
            # Método 3: settings
            if not api_key:
                api_key = getattr(settings, 'OPENAI_API_KEY', None)
                print(f"Método 3 (settings): {api_key[:20] if api_key else 'None'}...")
            
            # Debug: imprimir TODAS las variables que contienen "OPENAI" o "API"
            env_debug = {k: (v[:20] + '...' if len(v) > 20 else v) 
                        for k, v in os.environ.items() 
                        if 'OPENAI' in k.upper() or 'API' in k.upper()}
            print(f"Variables con OPENAI/API: {env_debug}")
            
            if not api_key:
                return render(request, "upload_photo.html", {
                    "error": f"API Key no encontrada. Variables encontradas: {list(env_debug.keys())}",
                    "category": category,
                    "subcategory": subcategory,
                    "view_name": view_name
                })
            
            client = OpenAI(api_key=api_key)
            prompt = get_prompt(category, subcategory, view_name)
            
            photo.seek(0)
            image_bytes = photo.read()
            
            response = client.images.edit(
                model="dall-e-2",
                image=image_bytes,
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
                "error": f"Error: {str(e)}",
                "category": category,
                "subcategory": subcategory,
                "view_name": view_name
            })
    
    return render(request, "upload_photo.html", {
        "category": category,
        "subcategory": subcategory,
        "view_name": view_name
    })