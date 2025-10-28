from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)
# products/models.py
from django.db import models
import os
from uuid import uuid4

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

class Category(models.Model):
    from django.db import models

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)


class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class ViewOption(models.Model):
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    thumbnail = models.ImageField(upload_to='thumbnails/')
    prompt = models.TextField()

    def __str__(self):
        return f"{self.subcategory.name} - {self.name}"
class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to=upload_subcategory_image, blank=True, null=True)

    class Meta:
        unique_together = ('category', 'name')

    def __str__(self):
        return f'{self.category.name} / {self.name}'

class ViewOption(models.Model):
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='views')
    name = models.CharField(max_length=200)
    prompt = models.TextField(blank=True, default='')

    def __str__(self):
        return f'{self.subcategory} - {self.name}'

class GeneratedImage(models.Model):
    input_image = models.ImageField(upload_to=upload_input_path)
    output_image = models.ImageField(upload_to=upload_output_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
