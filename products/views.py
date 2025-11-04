from django.shortcuts import render
from django.http import HttpResponse

def select_category(request):
    categories = ["Calzado", "Complementos", "Joyas", "Moda"]
    return render(request, "select_category.html", {"categories": categories})


def select_subcategory(request, category):
    subcategories = {
        "Moda": ["Camisa_Hombre", "Camisetas", "Polos"],
        "Calzado": ["Deportivos", "Botas", "Sandalias"],
        "Complementos": ["Gafas", "Cinturones", "Sombreros"],
        "Joyas": ["Collares", "Anillos", "Pulseras"]
    }
    return render(request, "select_subcategory.html", {
        "category": category,
        "subcategories": subcategories.get(category, [])
    })


def view_products(request, category, subcategory):
    # Importante: pasamos subcategory al template correctamente
    views = [
        {"name": "vista1", "image": "/static/img/vista1.png"},
        {"name": "vista2", "image": "/static/img/vista2.png"},
    ]
    context = {
        "category": category,
        "subcategory": subcategory,
        "views": views
    }
    return render(request, "view_products.html", context)


def upload_photo(request, category, subcategory, view_name):
    # Página de subida de imagen con feedback visual
    if request.method == "POST" and request.FILES.get("photo"):
        photo = request.FILES["photo"]

        # Validación de formato de imagen
        if not photo.name.lower().endswith((".jpg", ".jpeg", ".png")):
            return render(request, "upload_photo.html", {
                "category": category,
                "subcategory": subcategory,
                "view_name": view_name,
                "error": "Formato no válido. Sube una imagen JPG o PNG."
            })

        # Simulación de imagen procesada (luego irá la API real)
        result_url = "https://via.placeholder.com/512x512?text=Imagen+procesada"

        return render(request, "upload_photo.html", {
            "category": category,
            "subcategory": subcategory,
            "view_name": view_name,
            "success": True,
            "result_image": result_url
        })

    return render(request, "upload_photo.html", {
        "category": category,
        "subcategory": subcategory,
        "view_name": view_name
    })
