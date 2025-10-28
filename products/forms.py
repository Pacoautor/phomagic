from django import forms

class ImageUploadForm(forms.Form):
    image = forms.ImageField(label="Sube tu imagen")
CATEGORIAS = [
    ("Moda (textil)", "Moda (textil)"),
    ("Accesorios", "Accesorios"),
    ("Calzado", "Calzado"),
]

SUBCATEGORIAS = [
    ("Camisetas cuello redondo manga corta", "Camisetas cuello redondo manga corta"),
    ("Camisetas polo", "Camisetas polo"),
    ("Sudaderas", "Sudaderas"),
]

TAMANOS = [("Pequeño", "Pequeño"), ("Mediano", "Mediano"), ("Grande", "Grande")]

COLORES_FONDO = [
    ("Blanco (#FFFFFF)", "Blanco (#FFFFFF)"),
    ("Transparente", "Transparente"),
    ("Negro (#000000)", "Negro (#000000)"),
]

class SelectCategoryForm(forms.Form):
    categoria = forms.ChoiceField(choices=CATEGORIAS, label="Categoría")
    subcategoria = forms.ChoiceField(choices=SUBCATEGORIAS, label="Subcategoría")
    tamano = forms.ChoiceField(choices=TAMANOS, label="Tamaño requerido")
    color_fondo = forms.ChoiceField(choices=COLORES_FONDO, label="Color de fondo")
    seguimiento_logo = forms.BooleanField(
        label="Seguimiento de logotipo (Sí/No)", required=False
    )
