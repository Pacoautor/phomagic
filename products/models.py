# products/models.py
from django.db import models
from django.utils.text import slugify

# ============
# IMPORTANTE:
# Estas funciones las necesitan migraciones antiguas.
# No las borres, aunque tus modelos actuales no las usen.
# ============
def upload_input_path(instance, filename):
    # Ruta de subida para imágenes de entrada históricas (usadas por migraciones)
    return f"uploads/input/{filename}"

def upload_output_path(instance, filename):
    # Ruta de subida para imágenes de salida históricas (usadas por migraciones)
    return f"uploads/output/{filename}"


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    # Archivo real (no URL)
    image = models.ImageField(upload_to="category/", blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=160, blank=True)
    image = models.ImageField(upload_to="subcategory/", blank=True, null=True)

    class Meta:
        unique_together = ("category", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.category.name} / {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ViewOption(models.Model):
    subcategory = models.ForeignKey(Subcategory, on_delete=models.CASCADE, related_name="view_options")
    name = models.CharField(max_length=120)
    image = models.ImageField(upload_to="viewoption/", blank=True, null=True)
    # Prompt secreto por vista (opcional)
    prompt_override = models.TextField(blank=True, null=True, help_text="(Opcional) Prompt secreto para esta vista.")

    class Meta:
        unique_together = ("subcategory", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.subcategory} / {self.name}"
