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
        
        result_url = "https://via.placeholder.com/512x512?text=Procesado"
        return render(request, "upload_photo.html", {
            "success": True,
            "result_image": result_url,
            "category": category,
            "subcategory": subcategory,
            "view_name": view_name
        })
    
    return render(request, "upload_photo.html", {
        "category": category,
        "subcategory": subcategory,
        "view_name": view_name
    })