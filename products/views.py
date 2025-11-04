from django.conf import settings
from django.shortcuts import render
from django.core.files.storage import default_storage
import os
import requests
from bs4 import BeautifulSoup


def get_remote_folders(url):
    """Lee las carpetas en un índice remoto (InfinityFree)."""
    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        folders = []

        for link in soup.find_all("a"):
            name = link.get("href").strip("/")
            # Evitamos carpetas del sistema o vacías
            if name not in ["Parent Directory", "", ".keep", ".refresh"]:
                folders.append(name)
        return folders

    except Exception as e:
        print(f"⚠️ Error leyendo {url}: {e}")
        return []


def select_category(request):
    """Muestra las categorías principales desde el hosting remoto."""
    base_url = settings.MEDIA_URL + "lineas/"
    categories = get_remote_folders(base_url)

    return render(request, "select_category.html", {"categories": categories})


def select_subcategory(request, category_name):
    """Muestra las subcategorías dentro de una categoría."""
    category_url = f"{settings.MEDIA_URL}lineas/{category_name}/"
    subcategories = get_remote_folders(category_url)

    return render(request, "select_subcategory.html", {
        "category_name": category_name,
        "subcategories": subcategories
    })


def select_view(request, category_name, subcategory_name):
    """Muestra las vistas dentro de la subcategoría."""
    try:
        url = f"{settings.MEDIA_URL}lineas/{category_name}/{subcategory_name}/"
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        views = []

        for link in soup.find_all("a"):
            href = link.get("href")
            if href.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                views.append(f"{url}{href}")

    except Exception as e:
        print(f"⚠️ Error leyendo vistas de {url}: {e}")
        views = []

    return render(request, "select_view.html", {
        "category_name": category_name,
        "subcategory_name": subcategory_name,
        "views": views
    })


def upload_photo(request):
    """Carga de fotos al servidor principal (Render)."""
    if request.method == "POST" and request.FILES.get("photo"):
        photo = request.FILES["photo"]
        save_path = os.path.join(settings.MEDIA_ROOT, "uploads", photo.name)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with default_storage.open(save_path, "wb+") as destination:
            for chunk in photo.chunks():
                destination.write(chunk)

        return render(request, "upload_photo.html", {"message": "Imagen subida correctamente."})

    return render(request, "upload_photo.html")
