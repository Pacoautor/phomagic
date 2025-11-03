from django.conf import settings
from django.shortcuts import render
from pathlib import Path

def select_category(request):
    base_path = Path(settings.MEDIA_ROOT) / 'lineas'
    categories = []

    if base_path.exists():
        for item in base_path.iterdir():
            if item.is_dir():
                categories.append(item.name)
    else:
        print("⚠️ No se encontró la carpeta:", base_path)

    return render(request, 'select_category.html', {'categories': categories})


def select_subcategory(request, category_name):
    category_path = Path(settings.MEDIA_ROOT) / 'lineas' / category_name
    subcategories = []

    if category_path.exists():
        for item in category_path.iterdir():
            if item.is_dir():
                subcategories.append(item.name)

    return render(request, 'select_subcategory.html', {
        'category_name': category_name,
        'subcategories': subcategories
    })


def select_view(request, category_name, subcategory_name):
    sub_path = Path(settings.MEDIA_ROOT) / 'lineas' / category_name / subcategory_name
    views = []

    if sub_path.exists():
        for item in sub_path.iterdir():
            if item.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif']:
                views.append(f'{settings.MEDIA_URL}lineas/{category_name}/{subcategory_name}/{item.name}')

    return render(request, 'select_view.html', {
        'category_name': category_name,
        'subcategory_name': subcategory_name,
        'views': views
    })
