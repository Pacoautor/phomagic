import os
import openai
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import Category, SubCategory, ViewOption
from .forms import ImageUploadForm
from .utils import validate_image_quality

# Configura la clave de OpenAI
openai.api_key = settings.OPENAI_API_KEY


# --- Vista principal ---
def index(request):
    categories = Category.objects.all()
    return render(request, 'index.html', {'categories': categories})


# --- Cargar subcategorías ---
def load_subcategories(request):
    category_id = request.GET.get('category_id')
    subcategories = SubCategory.objects.filter(category_id=category_id)
    return JsonResponse(list(subcategories.values('id', 'name')), safe=False)


# --- Cargar vistas ---
def load_views(request):
    subcat_id = request.GET.get('subcategory_id')
    views = ViewOption.objects.filter(subcategory_id=subcat_id)
    return JsonResponse(list(views.values('id', 'name', 'thumbnail')), safe=False)


# --- Subir imagen y mostrar miniaturas ---
def upload_image(request):
    base_path = os.path.join(settings.BASE_DIR, 'products', 'lineas')

    categoria = request.GET.get('categoria', 'Moda')
    subcategoria = request.GET.get('subcategoria', 'Camisetas cuello redondo manga corta')

    folder_path = os.path.join(base_path, categoria, subcategoria)
    miniaturas = []

    if os.path.exists(folder_path):
        for file in os.listdir(folder_path):
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                prompt_file = os.path.splitext(file)[0] + '.txt'
                prompt_path = os.path.join(folder_path, prompt_file)

                prompt_text = ''
                if os.path.exists(prompt_path):
                    with open(prompt_path, 'r', encoding='utf-8') as f:
                        prompt_text = f.read()

                miniaturas.append({
                    'image': f'/static/lineas/{categoria}/{subcategoria}/{file}',
                    'prompt': prompt_text,
                    'nombre': file
                })

    context = {
        'categoria': categoria,
        'subcategoria': subcategoria,
        'miniaturas': miniaturas
    }
    return render(request, 'upload.html', context)


# --- Procesar imagen con OpenAI ---
def process_image(request):
    if request.method == 'POST':
        prompt = request.POST.get('prompt', '')
        uploaded_image = request.FILES.get('input_image')

        if not uploaded_image or not prompt:
            return render(request, 'error.html', {'message': 'Faltan datos para procesar la imagen.'})

        try:
            # Llamada al modelo de OpenAI (gpt-image-1)
            result = openai.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                image=uploaded_image.read()
            )

            generated_url = result.data[0].url
            return render(request, 'result.html', {'image_url': generated_url})

        except Exception as e:
            return render(request, 'error.html', {'message': str(e)})

    # Si se accede por GET, redirigimos al inicio
    return redirect('home')
