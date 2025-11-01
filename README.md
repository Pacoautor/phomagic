# 📸 Phomagic — Sistema de Procesamiento de Imágenes con Vistas y Categorías

## 🔒 Documento de referencia oficial (versión estable)
> Este archivo define la arquitectura, estructura de carpetas, y flujo funcional **definitivo** del proyecto Phomagic.  
> Cualquier cambio a partir de aquí deberá respetar este esquema base.

---

## 🧱 ESTRUCTURA OFICIAL DE ARCHIVOS

Toda la lógica de vistas y miniaturas parte del siguiente árbol dentro de `/media/lineas/`.

media/
└── lineas/
├── Calzado/
│ ├── vista1.png
│ ├── vista1.docx
│ ├── vista2.png
│ └── vista2.docx
├── Complementos/
│ ├── vista1.png
│ └── vista1.docx
├── Joyas/
│ ├── vista1.png
│ └── vista1.docx
└── Moda textil_Camisetas cuello redondo manga corta/
├── vista1.png
├── vista1.docx
└── vista2.png


✅ Cada **carpeta de primer nivel** dentro de `lineas` representa una **categoría**.  
✅ Dentro de cada categoría se guardan las **vistas**, cada una con:
- Un archivo `.png` → miniatura visible en la web  
- Un archivo `.docx` → prompt o descripción textual asociada  

🧩 Estas carpetas son **dinámicas y escalables**:  
Paco puede añadir o eliminar nuevas categorías y vistas en cualquier momento.  
El sistema las detecta automáticamente al iniciar.

---

## ⚙️ CONFIGURACIÓN EN `settings.py`

Rutas de medios y constantes:

```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
LINEAS_ROOT = MEDIA_ROOT / 'lineas'
