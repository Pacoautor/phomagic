from django.db import migrations, models
from django.utils.text import slugify


def fix_slugs_forward(apps, schema_editor):
    Category = apps.get_model('products', 'Category')
    Subcategory = apps.get_model('products', 'Subcategory')

    # --- Normaliza slugs de Category (únicos globalmente) ---
    seen = set()
    for c in Category.objects.all().order_by('id'):
        base = slugify(c.name) or f"categoria-{c.id}"
        s = base
        i = 2
        # Evita colisiones con otras filas ya existentes
        while s in seen or Category.objects.exclude(pk=c.pk).filter(slug=s).exists():
            s = f"{base}-{i}"
            i += 1
        c.slug = s
        c.save(update_fields=["slug"])
        seen.add(s)

    # --- Normaliza slugs de Subcategory (únicos dentro de category) ---
    from collections import defaultdict
    seen_per_cat = defaultdict(set)
    for sc in Subcategory.objects.select_related("category").all().order_by('id'):
        base = slugify(sc.name) or f"subcategoria-{sc.id}"
        cid = sc.category_id
        s = base
        i = 2
        while (s in seen_per_cat[cid] or
               Subcategory.objects.filter(category_id=cid, slug=s).exclude(pk=sc.pk).exists()):
            s = f"{base}-{i}"
            i += 1
        sc.slug = s
        sc.save(update_fields=["slug"])
        seen_per_cat[cid].add(s)


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0005_alter_category_options_alter_subcategory_options_and_more'),
    ]

    operations = [
        # Asegura que los campos existen antes (si ya existen, no pasa nada)
        migrations.AddField(
            model_name='category',
            name='sort_order',
            field=models.PositiveSmallIntegerField(default=10),
        ),
        migrations.AddField(
            model_name='subcategory',
            name='sort_order',
            field=models.PositiveSmallIntegerField(default=10),
        ),

        # Limpieza de datos ANTES de imponer unicidad
        migrations.RunPython(fix_slugs_forward, reverse_code=migrations.RunPython.noop),

        # Unicidad real en Category.slug
        migrations.AlterField(
            model_name='category',
            name='slug',
            field=models.SlugField(max_length=200, unique=True, db_index=True),
        ),

        # Slug obligatorio en Subcategory
        migrations.AlterField(
            model_name='subcategory',
            name='slug',
            field=models.SlugField(max_length=200, db_index=True),
        ),

        # Unicidad por categoría en Subcategory
        migrations.AddConstraint(
            model_name='subcategory',
            constraint=models.UniqueConstraint(fields=['category', 'slug'], name='uniq_subcat_per_cat'),
        ),
    ]
