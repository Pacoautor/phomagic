import os
from django.core.management.base import BaseCommand
from products.models import Category, SubCategory, ViewOption
from django.core.files import File
from django.conf import settings


class Command(BaseCommand):
    help = "Importa categorías, subcategorías, vistas y prompts desde la carpeta products/lineas"

    def handle(self, *args, **options):
        base_path = os.path.join(settings.BASE_DIR, 'products', 'lineas')

        if not os.path.exists(base_path):
            self.stdout.write(self.style.ERROR(f"❌ No existe la carpeta {base_path}"))
            return

        self.stdout.write(self.style.NOTICE(f"Iniciando importación desde {base_path}...\n"))

        for category_name in os.listdir(base_path):
            category_path = os.path.join(base_path, category_name)
            if not os.path.isdir(category_path):
                continue

            category, _ = Category.objects.get_or_create(name=category_name)
            self.stdout.write(self.style.SUCCESS(f"📂 Categoría creada o existente: {category.name}"))

            for subcategory_name in os.listdir(category_path):
                sub_path = os.path.join(category_path, subcategory_name)
                if not os.path.isdir(sub_path):
                    continue

                subcategory, _ = SubCategory.objects.get_or_create(
                    category=category, name=subcategory_name
                )
                self.stdout.write(f"  📁 Subcategoría: {subcategory.name}")

                # Iterar sobre las imágenes de la subcategoría
                for file_name in os.listdir(sub_path):
                    if file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                        image_path = os.path.join(sub_path, file_name)
                        view_name = os.path.splitext(file_name)[0]

                        # Buscar archivo .txt con el mismo nombre que la imagen
                        prompt_file = os.path.join(sub_path, f"{view_name}.txt")
                        prompt_text = ""
                        if os.path.exists(prompt_file):
                            with open(prompt_file, "r", encoding="utf-8") as f:
                                prompt_text = f.read().strip()
                            self.stdout.write(f"    🧠 Prompt encontrado para {view_name}")
                        else:
                            self.stdout.write(f"    ⚠️ No se encontró prompt para {view_name} (se dejará vacío)")

                        # Crear o actualizar la vista
                        with open(image_path, 'rb') as img_file:
                            view_option, created = ViewOption.objects.get_or_create(
                                subcategory=subcategory,
                                name=view_name,
                                defaults={'prompt': prompt_text}
                            )
                            if created:
                                view_option.thumbnail.save(file_name, File(img_file), save=True)
                                self.stdout.write(f"    ✅ Vista creada: {view_name}")
                            else:
                                # Si ya existía, actualizar prompt y miniatura
                                view_option.prompt = prompt_text
                                view_option.thumbnail.save(file_name, File(img_file), save=True)
                                view_option.save()
                                self.stdout.write(f"    🔄 Vista actualizada: {view_name}")

        self.stdout.write(self.style.SUCCESS("\n🎉 Importación completada con éxito."))
