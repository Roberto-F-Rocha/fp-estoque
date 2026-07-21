import re
from decimal import Decimal, InvalidOperation

from django.db import migrations, models


def migrate_existing_product_volume(apps, schema_editor):
    Product = apps.get_model("inventory", "Product")
    pattern = re.compile(r"(?P<volume>\d+(?:[.,]\d+)?)\s*(?P<unit>ml|l)\b", re.IGNORECASE)

    for product in Product.objects.all().iterator():
        package_type = product.package_type or ""
        match = pattern.search(package_type)
        if not match:
            continue

        try:
            volume = Decimal(match.group("volume").replace(",", "."))
        except (InvalidOperation, AttributeError):
            continue

        if volume <= 0:
            continue

        product.volume = volume
        product.volume_unit = match.group("unit").upper()
        product.package_type = pattern.sub("", package_type).strip(" -–—/")
        product.save(update_fields=["volume", "volume_unit", "package_type"])


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0004_complete_inventory_workflow"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="volume",
            field=models.DecimalField(decimal_places=3, default=1, max_digits=10),
        ),
        migrations.AddField(
            model_name="product",
            name="volume_unit",
            field=models.CharField(
                choices=[("ML", "Mililitro (mL)"), ("L", "Litro (L)")],
                default="L",
                max_length=2,
            ),
        ),
        migrations.RunPython(
            migrate_existing_product_volume,
            migrations.RunPython.noop,
        ),
    ]
