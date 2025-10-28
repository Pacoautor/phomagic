
from django.db import models
import os
from uuid import uuid4

# Funciones para rutas de subida de imágenes
def upload_category_image(instance, filename):
    ext = filename.split('.')[-1]
    return f'categories/{uuid4()}.{ext}'

def upload_subcategory_image(instance, filename):
    ext = filename.split('.')[-1]
    return f'subcategories/{uuid4()}.{ext}'

def upload_input_path(instance, filename):
    ext = filename.split('.')[-1]
    return f'uploads/input/{uuid4()}.{ext}'

def upload_output_path(instance, filename):
    ext = filename.split('.')[-1]
    return f'uploads/output/{uuid4()}.{ext}'


# Modelo Category
class Category(models.Model):
    category_name = models.CharField(max_length=200)
    image = models.ImageField(upload_to=upload_category_image, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.category_name


# Modelo SubCategory
class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to=upload_subcategory_image, blank=True, null=True)

    class Meta:
        unique_together = ('category', 'name')
        verbose_name_plural = "Subcategories"

    def __str__(self):
        return f'{self.category.category_name} / {self.name}'


# Modelo ViewOption
class ViewOption(models.Model):
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='views')
    name = models.CharField(max_length=200)
    prompt = models.TextField(blank=True, default='')

    def __str__(self):
        return f'{self.subcategory.name} - {self.name}'


# Modelo GeneratedImage
class GeneratedImage(models.Model):
    input_image = models.ImageField(upload_to=upload_input_path)
    output_image = models.ImageField(upload_to=upload_output_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Generated on {self.created_at.strftime("%Y-%m-%d %H:%M:%S")}'
