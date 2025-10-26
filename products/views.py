import os
import json
import uuid
import logging
from pathlib import Path
from django import forms
from django.conf import settings
from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from .forms import SelectCategoryForm

logger = logging.getLogger("django")

class UploadForm(forms.Form):
    image = forms.ImageField(label="Selecciona una imagen")

def ensure_dirs():
    base = Path(settings.MEDIA_ROOT)
    for sub in ("uploads/input", "uploads/output", "uploads/tmp"):
        (base / sub).mkdir(parents=True, exist_ok=True)

def select_category(request):
    ensure_dirs()
    if request.method == "POST":
        form = SelectCategoryForm(request.POST)
        if form.is_valid():
            request.session["selection"] = form.cleaned_data
            request.session.modified = True
            return redirect("upload_photo")
    else:
        form = SelectCategoryForm()
    return render(request, "products/select_category.html", {"form": form})

def upload_photo(request):
    ensure_dirs()
    selection = request.session.get("selection")
    if not selection:
        return redirect("select_category")
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.cleaned_data["image"]
            rel_path = default_storage.save(os.path.join("uploads/input", image.name), image)
            input_path = os.path.join(settings.MEDIA_ROOT, rel_path)
            job_id = str(uuid.uuid4())
            tmp_file = os.path.join(settings.MEDIA_ROOT, "uploads/tmp", f"{job_id}.json")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump({"selection": selection, "input_path": input_path}, f)
            request.session["job_id"] = job_id
            return redirect("processing")
    else:
        form = UploadForm()
    return render(request, "products/upload_photo.html", {"form": form, "selection": selection})

def processing(request):
    ensure_dirs()
    job_id = request.session.get("job_id")
    if not job_id:
        return redirect("select_category")
    tmp_file = os.path.join(settings.MEDIA_ROOT, "uploads/tmp", f"{job_id}.json")
    if not os.path.exists(tmp_file):
        return redirect("select_category")
    output_path = os.path.join(settings.MEDIA_ROOT, "uploads/output", f"{job_id}.png")
    from PIL import Image
    img = Image.new("RGB", (400, 400), (255, 255, 255))
    img.save(output_path)
    request.session["output_path"] = output_path
    return redirect("result")

def result(request):
    ensure_dirs()
    output_path = request.session.get("output_path")
    selection = request.session.get("selection", {})
    return render(request, "products/result.html", {"output_path": output_path, "selection": selection})
