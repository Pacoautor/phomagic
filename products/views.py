
from django.conf import settings
from django.shortcuts import render
from pathlib import Path

def select_category(request):
    # Ruta base dentro de /media/lineas/
    base_path = Path(settings.MEDIA_ROOT) / 'lineas'
    categories = []

    try:
        if base_path.exists():
            for item in base_path.iterdir():
                if item.is_dir():
                    categories.append(item.name)
    except Exception as e:
        print(f"⚠️ Error leyendo categorías: {e}")

    return render(request, 'select_category.html', {'categories': categories})


def select_subcategory(request, category_name):
    category_path = Path(settings.MEDIA_ROOT) / 'lineas' / category_name
    subcategories = []

    try:
        if category_path.exists():
            for item in category_path.iterdir():
                if item.is_dir():
                    subcategories.append(item.name)
    except Exception as e:
        print(f"⚠️ Error leyendo subcategorías: {e}")

    return render(request, 'select_subcategory.html', {
        'category_name': category_name,
        'subcategories': subcategories
    })


def select_view(request, category_name, subcategory_name):
    sub_path = Path(settings.MEDIA_ROOT) / 'lineas' / category_name / subcategory_name
    views = []

    try:
        if sub_path.exists():
            for item in sub_path.iterdir():
                if item.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif']:
                    views.append(f'{settings.MEDIA_URL}lineas/{category_name}/{subcategory_name}/{item.name}')
    except Exception as e:
        print(f"⚠️ Error leyendo vistas: {e}")

    return render(request, 'select_view.html', {
        'category_name': category_name,
        'subcategory_name': subcategory_name,
        'views': views
    })
from django.shortcuts import render
from django.core.files.storage import default_storage
from django.conf import settings
import os

def upload_photo(request):
    if request.method == "POST" and request.FILES.get("photo"):
        photo = request.FILES["photo"]
        save_path = os.path.join(settings.MEDIA_ROOT, "uploads", photo.name)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with default_storage.open(save_path, "wb+") as destination:
            for chunk in photo.chunks():
                destination.write(chunk)
        return render(request, "upload_photo.html", {"message": "Imagen subida correctamente."})
    return render(request, "upload_photo.html")
