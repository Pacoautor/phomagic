import os
from django.shortcuts import render

# Base de medios en InfinityFree
MEDIA_URL = "https://fgrautor.free.nf/media/lineas"

def select_category(request):
    categories = ["calzado", "complementos", "joyas", "moda"]
    return render(request, "select_category.html", {"categories": categories, "media_url": MEDIA_URL})

def select_subcategory(request, category):
    subcategories = []
    path = os.path.join("media", "lineas", category)
    try:
        subcategories = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    except FileNotFoundError:
        pass
    return render(request, "select_subcategory.html", {"category": category, "subcategories": subcategories, "media_url": MEDIA_URL})

def view_products(request, category, subcategory):
    product_dir = os.path.join("media", "lineas", category, subcategory)
    images = []
    try:
        images = [f"{MEDIA_URL}/{category}/{subcategory}/{f}" for f in os.listdir(product_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    except FileNotFoundError:
        pass
    return render(request, "view_products.html", {"category": category, "subcategory": subcategory, "images": images})
