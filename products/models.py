# products/models.py
from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to="category_images/", blank=True, null=True)

    def __str__(self):
        return self.name


class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    image = models.ImageField(upload_to="subcategory_images/", blank=True, null=True)

    class Meta:
        unique_together = ("category", "name")

    def __str__(self):
        return f"{self.category} / {self.name}"


class ViewOption(models.Model):
    """Nuevo nivel: Vista (frontal, 45 izq, etc.) dependiente de la Subcategoría."""
    subcategory = models.ForeignKey(Subcategory, on_delete=models.CASCADE, related_name="views")
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="view_images/", blank=True, null=True)

    class Meta:
        unique_together = ("subcategory", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.subcategory} / {self.name}"


class MasterPrompt(models.Model):
    """Ahora el prompt puede depender de Subcategoría y de Vista (opcional)."""
    subcategory = models.ForeignKey(Subcategory, on_delete=models.CASCADE)
    view = models.ForeignKey(ViewOption, on_delete=models.CASCADE, blank=True, null=True)
    prompt_text = models.TextField()
    reference_photo = models.ImageField(upload_to="reference_photos/", blank=True, null=True)

    def __str__(self):
        v = f" [{self.view.name}]" if self.view else ""
        return f"Prompt: {self.subcategory}{v}"
