import os
import io
import tempfile
import openai
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import Category, SubCategory, ViewOption
from .forms import ImageUploadForm
from .utils import validate_image_quality

# Configura la API de OpenAI
openai.api_key = settings.OPENAI_API_KEY


# 🔹 Página principal — muestra categorías
def index(request):
    categories = Category.objects.all()
    return render(request, 'index.html', {'categories': categories})


# 🔹 Cargar subcategorías según la categoría seleccionada
def load_subcategories(request):
    category_id = request.GET.get('category_id')
    subcategories = SubCategory.objects.filter(category_id=category_id)
    return JsonResponse(list(subcategories.values('id', 'name')), safe=False)


# 🔹 Cargar vistas según la subcategoría
def load_views(request):
    subcat_id = request.GET.get('subcategory_id')
    views = ViewOption.objects.filter(subcategory_id=subcat_id)
    return JsonResponse(list(views.values('id', 'name', 'thumbnail')), safe=False)


# 🔹 Mostrar formulario de subida de imagen
def upload_image(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            request.session['selection'] = form.cleaned_data
            return redirect('process_image')
    else:
        form = ImageUploadForm()

    return render(request, 'upload.html', {'form': form})


# 🔹 Validar y procesar la imagen con OpenAI
def process_image(request):
    if request.method == 'POST':
        prompt = request.POST.get('prompt', '')
        uploaded_image = request.FILES.get('input_image')

        if not uploaded_image or not prompt:
            return render(request, 'error.html', {'message': 'Faltan datos para procesar la imagen.'})

        # 🔸 Validación básica antes de enviar
        is_valid, error_message = validate_image_quality(uploaded_image)
        if not is_valid:
            return render(request, 'error.html', {'message': error_message})

        try:
            # 🔸 Guardar la imagen temporalmente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                for chunk in uploaded_image.chunks():
                    tmp.write(chunk)
                temp_path = tmp.name

            # 🔸 Llamar al modelo de OpenAI correctamente
            response = openai.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                image=open(temp_path, "rb")
            )

            generated_url = response.data[0].url

            # 🔸 Eliminar archivo temporal
            os.remove(temp_path)

            return render(request, 'result.html', {'image_url': generated_url})

        except Exception as e:
            return render(request, 'error.html', {'message': f"Error al procesar imagen: {str(e)}"})

    # Si se accede por GET, redirigir al inicio
    return redirect('home')
