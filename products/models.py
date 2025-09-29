from django.conf import settings
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    # Puede que ya lo tengas; si no, el slug es opcional para URLs limpias
    slug = models.SlugField(max_length=120, unique=True, blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=100)
    image_url = models.URLField(blank=True, null=True)

    class Meta:
        unique_together = ("category", "name")
        ordering = ["category__name", "name"]

    def __str__(self):
        return f"{self.category.name} / {self.name}"


class ViewOption(models.Model):
    subcategory = models.ForeignKey(Subcategory, on_delete=models.CASCADE, related_name="view_options")
    name = models.CharField(max_length=100)
    # Prompt maestro (NO se muestra al usuario)
    prompt = models.TextField(blank=True, default="")
    negative_prompt = models.TextField(blank=True, default="")
    strength = models.FloatField(default=0.8)
    image_url = models.URLField(blank=True, null=True)  # imagen de ejemplo para la tarjeta

    class Meta:
        unique_together = ("subcategory", "name")
        ordering = ["subcategory__category__name", "subcategory__name", "name"]

    def __str__(self):
        return f"{self.subcategory} / {self.name}"


def upload_input_path(instance, filename):
    return f"uploads/{filename}"


def upload_output_path(instance, filename):
    return f"generated/{filename}"


class GeneratedImage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="generated_images"
    )
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="generated_images")
    subcategory = models.ForeignKey(Subcategory, on_delete=models.SET_NULL, null=True, related_name="generated_images")
    view_option = models.ForeignKey(ViewOption, on_delete=models.SET_NULL, null=True, related_name="generated_images")

    # Guardamos las rutas en disco (Render usa FileSystemStorage por defecto)
    input_image = models.FileField(upload_to=upload_input_path, blank=True, null=True)
    output_image = models.FileField(upload_to=upload_output_path, blank=True, null=True)

    prompt_used = models.TextField(blank=True, default="")
    negative_prompt = models.TextField(blank=True, default="")
    strength = models.FloatField(default=0.8)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        u = getattr(self.user, "username", "anon")
        return f"{u} · {self.view_option or 'view'} · {self.created_at:%Y-%m-%d %H:%M}"
