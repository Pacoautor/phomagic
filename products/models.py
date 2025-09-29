from uuid import uuid4
import os
from datetime import datetime

from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


# ----- Helpers de subida -----
def _ext(filename: str) -> str:
    return os.path.splitext(filename)[1].lower() or ".jpg"


def upload_category_image(instance, filename):
    today = datetime.now().strftime("%Y/%m/%d")
    return f"category_images/{today}/{uuid4().hex}{_ext(filename)}"


def upload_subcategory_image(instance, filename):
    today = datetime.now().strftime("%Y/%m/%d")
    return f"subcategory_images/{today}/{uuid4().hex}{_ext(filename)}"


def upload_input_path(instance, filename):
    today = datetime.now().strftime("%Y/%m/%d")
    return f"generated_inputs/{today}/{uuid4().hex}{_ext(filename)}"


def upload_output_path(instance, filename):
    today = datetime.now().strftime("%Y/%m/%d")
    return f"generated_outputs/{today}/{uuid4().hex}{_ext(filename)}"


# ----- Modelos -----
class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    image = models.ImageField(upload_to=upload_category_image, blank=True, null=True)

    # Orden editable (0..10)
    sort_order = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        db_index=True,
        help_text="Orden de la categoría (0..10).",
    )

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80, unique=True)
    image = models.ImageField(upload_to=upload_subcategory_image, blank=True, null=True)

    # Orden editable (0..10)
    sort_order = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        db_index=True,
        help_text="Orden de la subcategoría (0..10).",
    )

    class Meta:
        ordering = ("sort_order", "name")
        unique_together = ("category", "name")
        verbose_name = "Subcategory"
        verbose_name_plural = "Subcategories"

    def __str__(self):
        return f"{self.category.name} / {self.name}"


class ViewOption(models.Model):
    """
    Opción de vista dentro de una subcategoría. Aquí guardas el PROMPT (privado).
    """
    subcategory = models.ForeignKey(Subcategory, on_delete=models.CASCADE, related_name="view_options")
    name = models.CharField(max_length=120)
    # Prompt interno (no se enseña al cliente)
    prompt = models.TextField(blank=True, default="")

    class Meta:
        ordering = ("subcategory__sort_order", "name")

    def __str__(self):
        return f"{self.subcategory} / {self.name}"


class GeneratedImage(models.Model):
    """
    Registro de generación: entrada del cliente + salida final (ya con borde de 50px).
    """
    subcategory = models.ForeignKey(Subcategory, on_delete=models.SET_NULL, null=True, blank=True)
    viewoption = models.ForeignKey(ViewOption, on_delete=models.SET_NULL, null=True, blank=True)
    input_image = models.ImageField(upload_to=upload_input_path, blank=True, null=True)
    output_image = models.ImageField(upload_to=upload_output_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Generated {self.pk} ({self.created_at:%Y-%m-%d %H:%M})"
