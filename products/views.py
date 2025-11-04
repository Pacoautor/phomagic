from django.shortcuts import render, redirect
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
    # Aquí se muestran las vistas/miniaturas disponibles
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
        # Aquí iría la validación de la imagen y envío a OpenAI API
        # De momento mostramos el nombre de la vista seleccionada
        return render(request, "upload_photo.html", {
            "category": category,
            "subcategory": subcategory,
            "view_name": view_name,
            "result_image": "https://via.placeholder.com/512x512?text=Imagen+Procesada",
            "success": True
        })

    return render(request, "upload_photo.html", {
        "category": category,
        "subcategory": subcategory,
        "view_name": view_name
    })
