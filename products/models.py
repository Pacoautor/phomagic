from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)  # NUEVO

    def __str__(self):
        return self.name


class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="subcategories/", blank=True, null=True)  # NUEVO

    class Meta:
        unique_together = ("category", "name")

    def __str__(self):
        return f"{self.category.name} · {self.name}"


# Tabla para los prompts maestros y fotos de referencia
class MasterPrompt(models.Model):
    subcategory = models.ForeignKey(Subcategory, on_delete=models.CASCADE)
    reference_name = models.CharField(max_length=100)
    reference_photo = models.ImageField(upload_to='reference_photos/')
    prompt_text = models.TextField()

    def __str__(self):
        return self.reference_name
