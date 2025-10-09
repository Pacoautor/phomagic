# products/forms.py
from django import forms

CATEGORY_CHOICES = [
    ('Moda', 'Moda (textil)'),
    ('Complementos', 'Complementos'),
    ('Calzado', 'Calzado'),
    ('Electrodomésticos', 'Electrodomésticos'),
    ('Joyas', 'Joyas'),
    ('Relojes', 'Relojes'),
]

# Subcategorías solo para "Moda" (puedes ampliarlas igual para otras categorías)
SUBCATEGORIES_BY_CATEGORY = {
    'Moda': [
        'Camisetas cuello redondo manga corta',
        'Camisetas cuello redondo manga larga',
        'Polos manga corta',
        'Polos manga larga',
        'Camisa de hombre manga larga',
        'Camisa de hombre manga corta',
        'Pantalón hombre largo',
        'Pantalón hombre corto',
        'Chaqueta (americana) Hombre',
        'Camisa de mujer manga larga',
        'Camisa de mujer manga corta',
        'Pantalón mujer largo',
        'Pantalón mujer corto',
        'Chaqueta (americana) Mujer',
        'Falda',
        'Vestido',
        'Jersey manga larga',
    ],
    # Puedes añadir subcategorías para otras categorías si lo deseas
}

SIZE_CHOICES = [
    ('S', 'Pequeño'),
    ('M', 'Medio'),
    ('L', 'Grande'),
    ('XL', 'Extra grande'),
]

BACKGROUND_CHOICES = [
    ('#FFFFFF', 'Blanco (#FFFFFF)'),
    ('#000000', 'Negro (#000000)'),
    ('#F5F5F5', 'Gris claro (#F5F5F5)'),
    ('#FF0000', 'Rojo (#FF0000)'),
    ('#00FF00', 'Verde (#00FF00)'),
    ('#0000FF', 'Azul (#0000FF)'),
]

class SelectCategoryForm(forms.Form):
    category = forms.ChoiceField(choices=CATEGORY_CHOICES, label='Categoría')
    subcategory = forms.ChoiceField(choices=[], label='Subcategoría')
    size = forms.ChoiceField(choices=SIZE_CHOICES, label='Tamaño requerido')
    background = forms.ChoiceField(choices=BACKGROUND_CHOICES, label='Color de fondo')
    follow_logo = forms.BooleanField(required=False, label='Seguimiento de logotipo (Sí/No)')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Poblar subcategorías dinámicamente según categoría seleccionada
        data = self.data or self.initial
        selected_cat = data.get('category', 'Moda')
        subs = SUBCATEGORIES_BY_CATEGORY.get(selected_cat, [])
        self.fields['subcategory'].choices = [(s, s) for s in subs]

class UploadPhotoForm(forms.Form):
    client_photo = forms.ImageField(label='Sube tu foto')

class ChooseViewForm(forms.Form):
    # Se llena con los números de los archivos encontrados en la carpeta
    view_number = forms.ChoiceField(choices=[], label='Selecciona la vista (número)')

    def __init__(self, *args, **kwargs):
        view_numbers = kwargs.pop('view_numbers', [])
        super().__init__(*args, **kwargs)
        self.fields['view_number'].choices = [(str(n), f'Vista {n}') for n in view_numbers]

class LogoForm(forms.Form):
    # Coordenadas del rectángulo en la imagen (en porcentaje 0-100 para evitar depender de píxeles exactos)
    rect_x = forms.FloatField(required=False, widget=forms.HiddenInput)
    rect_y = forms.FloatField(required=False, widget=forms.HiddenInput)
    rect_w = forms.FloatField(required=False, widget=forms.HiddenInput)
    rect_h = forms.FloatField(required=False, widget=forms.HiddenInput)
    logo_file = forms.ImageField(required=False, label='Sube tu logotipo (PNG/JPG con transparencia si es posible)')
