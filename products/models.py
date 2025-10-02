# --- Rutas de subida usadas por migraciones antiguas ---
import os
import uuid
from django.utils.text import slugify

def _safe_slug(obj, fallback: str) -> str:
    """
    Intenta obtener un slug razonable desde instance.slug o instance.name.
    Si no puede, usa el fallback. Nunca devuelve cadena vacía.
    """
    try:
        s = getattr(obj, "slug", None) or getattr(obj, "name", None) or fallback
    except Exception:
        s = fallback
    s = slugify(str(s)) or fallback
    return s

def upload_category_image(instance, filename):
    # p.ej: uploads/categories/moda/archivo.jpg
    base = _safe_slug(instance, "category")
    return os.path.join("uploads", "categories", base, filename)

def upload_subcategory_image(instance, filename):
    # p.ej: uploads/subcategories/camisetas/archivo.jpg
    base = _safe_slug(instance, "subcategory")
    return os.path.join("uploads", "subcategories", base, filename)

def upload_generated_input(instance, filename):
    # p.ej: uploads/generated/input/archivo.jpg
    return os.path.join("uploads", "generated", "input", filename)

def upload_generated_output(instance, filename):
    # p.ej: uploads/generated/output/archivo.jpg
    return os.path.join("uploads", "generated", "output", filename)

# --- Aliases para migraciones antiguas ---
def upload_input_path(instance, filename):
    """
    Alias para migraciones antiguas que usan este nombre.
    Genera un nombre único en carpeta inputs/.
    """
    name, ext = os.path.splitext(filename)
    new_name = f"{uuid.uuid4().hex}{ext.lower()}"
    return os.path.join("inputs", new_name)

def upload_output_path(instance, filename):
    """
    Alias para migraciones antiguas que usan este nombre.
    Genera un nombre único en carpeta outputs/.
    """
    name, ext = os.path.splitext(filename)
    new_name = f"{uuid.uuid4().hex}{ext.lower()}"
    return os.path.join("outputs", new_name)
# --- fin stubs ---


from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    # Imagen: si usas URL en admin, deja image_url; si usas archivos, cambia a ImageField
    image_url = models.URLField(blank=True, null=True)
    sort_order = models.PositiveSmallIntegerField(default=10)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Autogenera slug si está vacío (no pisa uno existente)
        if not self.slug:
            base = slugify(self.name) or "categoria"
            s = base
            i = 2
            while Category.objects.filter(slug=s).exclude(pk=self.pk).exists():
                s = f"{base}-{i}"
                i += 1
            self.slug = s
        super().save(*args, **kwargs)


class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=200, db_index=True)
    image_url = models.URLField(blank=True, null=True)
    sort_order = models.PositiveSmallIntegerField(default=10)

    class Meta:
        ordering = ["category__sort_order", "category__name", "sort_order", "name"]
        verbose_name = "Subcategoría"
        verbose_name_plural = "Subcategorías"
        constraints = [
            models.UniqueConstraint(fields=["category", "slug"], name="uniq_subcat_per_cat"),
        ]

    def __str__(self):
        return f"{self.category.name} / {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "subcategoria"
            s = base
            i = 2
            # Única por categoría
            while Subcategory.objects.filter(category=self.category, slug=s).exclude(pk=self.pk).exists():
                s = f"{base}-{i}"
                i += 1
            self.slug = s
        super().save(*args, **kwargs)


class ViewOption(models.Model):
    subcategory = models.ForeignKey(Subcategory, on_delete=models.CASCADE, related_name="viewoptions")
    name = models.CharField(max_length=150)
    prompt = models.TextField(blank=True, null=True)
    sort_order = models.PositiveSmallIntegerField(default=10)

    class Meta:
        ordering = ["subcategory__category__sort_order", "subcategory__sort_order", "sort_order", "name"]
        verbose_name = "Vista"
        verbose_name_plural = "Vistas"

    def __str__(self):
        return f"{self.subcategory.category.name} / {self.subcategory.name} / {self.name}"


class GeneratedImage(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    subcategory = models.ForeignKey(Subcategory, on_delete=models.SET_NULL, null=True, blank=True)
    viewoption = models.ForeignKey(ViewOption, on_delete=models.SET_NULL, null=True, blank=True)
    input_image = models.FileField(upload_to="inputs/", blank=True, null=True)
    output_image = models.FileField(upload_to="outputs/", blank=True, null=True)
