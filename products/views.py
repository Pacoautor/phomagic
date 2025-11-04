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
    views = [
        {"name": "vista1", "image": "/static/img/vista1.png"},
        {"name": "vista2", "image": "/static/img/vista2.png"},
    ]
    return render(request, "view_products.html", {
        "category": category,
        "subcategory": subcategory,
        "views": views
    })


def upload_photo(request, category, subcategory, view_name):
    if request.method == "POST" and request.FILES.get("photo"):
        photo = request.FILES["photo"]

        # Simulación de validación básica
        if not photo.name.lower().endswith((".jpg", ".jpeg", ".png")):
            return render(request, "upload_photo.html", {
                "category": category,
                "subcategory": subcategory,
                "view_name": view_name,
                "error": "Formato de archivo no válido. Sube JPG o PNG."
            })

        # Aquí se procesaría la imagen con la API de OpenAI
        result_url = "https://via.placeholder.com/512x512?text=Imagen+procesada"

        return render(request, "upload_photo.html", {
            "category": category,
            "subcategory": subcategory,
            "view_name": view_name,
            "result_image": result_url,
            "success": True
        })

    return render(request, "upload_photo.html", {
        "category": category,
        "subcategory": subcategory,
        "view_name": view_name
    })
