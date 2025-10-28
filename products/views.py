import openai
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from .models import Category, SubCategory, ViewOption
from .forms import ImageUploadForm
from .utils import validate_image_quality

openai.api_key = settings.OPENAI_API_KEY

def index(request):
    categories = Category.objects.all()
    return render(request, 'index.html', {'categories': categories})

def load_subcategories(request):
    category_id = request.GET.get('category_id')
    subcategories = SubCategory.objects.filter(category_id=category_id)
    return JsonResponse(list(subcategories.values('id', 'name')), safe=False)

def load_views(request):
    subcat_id = request.GET.get('subcategory_id')
    views = ViewOption.objects.filter(subcategory_id=subcat_id)
    return JsonResponse(list(views.values('id', 'name', 'thumbnail')), safe=False)

def upload_image(request, view_id):
    selected_view = ViewOption.objects.get(id=view_id)
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.cleaned_data['image']
            ok, msg = validate_image_quality(image)
            if not ok:
                return render(request, 'upload.html', {'form': form, 'error': msg})
            response = openai.images.generate(
                model="gpt-image-1",
                prompt=selected_view.prompt,
                image=image
            )
            processed_url = response.data[0].url
            return render(request, 'result.html', {'processed_url': processed_url})
    else:
        form = ImageUploadForm()
    return render(request, 'upload.html', {'form': form, 'view': selected_view})
