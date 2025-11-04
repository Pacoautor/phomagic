from django.shortcuts import render

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
        if not photo.name.lower().endswith((".jpg", ".jpeg", ".png")):
            return render(request, "upload_photo.html", {
                "error": "Formato no válido. Sube una imagen JPG o PNG.",
                "category": category,
                "subcategory": subcategory,
                "view_name": view_name
            })
        result_url = "https://via.placeholder.com/512x512?text=Imagen+procesada"
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
