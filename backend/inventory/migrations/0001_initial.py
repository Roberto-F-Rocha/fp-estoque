from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Supplier",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=180)),
                (
                    "document",
                    models.CharField(
                        blank=True,
                        max_length=20,
                        null=True,
                        unique=True,
                    ),
                ),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=50, unique=True)),
                (
                    "barcode",
                    models.CharField(
                        blank=True,
                        max_length=80,
                        null=True,
                        unique=True,
                    ),
                ),
                ("name", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("brand", models.CharField(blank=True, max_length=100)),
                ("unit", models.CharField(default="UN", max_length=20)),
                (
                    "cost_price",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                    ),
                ),
                (
                    "sale_price",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                    ),
                ),
                (
                    "stock",
                    models.DecimalField(
                        decimal_places=3,
                        default=0,
                        max_digits=12,
                    ),
                ),
                (
                    "minimum_stock",
                    models.DecimalField(
                        decimal_places=3,
                        default=0,
                        max_digits=12,
                    ),
                ),
                ("location", models.CharField(blank=True, max_length=100)),
                ("active", models.BooleanField(default=True)),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="products",
                        to="inventory.category",
                    ),
                ),
                (
                    "supplier",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="products",
                        to="inventory.supplier",
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
                "indexes": [
                    models.Index(
                        fields=["name"],
                        name="inv_product_name_idx",
                    )
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            cost_price__gte=0,
                            sale_price__gte=0,
                            stock__gte=0,
                            minimum_stock__gte=0,
                        ),
                        name="inventory_product_nonnegative_values",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="Lot",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("number", models.CharField(max_length=80)),
                (
                    "quantity",
                    models.DecimalField(
                        decimal_places=3,
                        default=0,
                        max_digits=12,
                    ),
                ),
                ("expiration_date", models.DateField(blank=True, null=True)),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lots",
                        to="inventory.product",
                    ),
                ),
                (
                    "supplier",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="inventory.supplier",
                    ),
                ),
            ],
            options={
                "ordering": ["expiration_date", "created_at"],
                "unique_together": {("product", "number")},
                "indexes": [
                    models.Index(
                        fields=["expiration_date"],
                        name="inv_lot_expiration_idx",
                    )
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(quantity__gte=0),
                        name="inventory_lot_quantity_nonnegative",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="Movement",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("IN", "Entrada"),
                            ("OUT", "Saída"),
                            ("ADJ+", "Ajuste positivo"),
                            ("ADJ-", "Ajuste negativo"),
                            ("REV", "Estorno"),
                        ],
                        max_length=5,
                    ),
                ),
                (
                    "quantity",
                    models.DecimalField(decimal_places=3, max_digits=12),
                ),
                (
                    "previous_stock",
                    models.DecimalField(decimal_places=3, max_digits=12),
                ),
                (
                    "final_stock",
                    models.DecimalField(decimal_places=3, max_digits=12),
                ),
                (
                    "unit_cost",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                    ),
                ),
                ("reason", models.CharField(blank=True, max_length=200)),
                ("notes", models.TextField(blank=True)),
                ("reversed", models.BooleanField(default=False)),
                (
                    "lot",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="inventory.lot",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="movements",
                        to="inventory.product",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_movements",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["-created_at"],
                        name="inv_movement_created_idx",
                    ),
                    models.Index(
                        fields=["type"],
                        name="inv_movement_type_idx",
                    ),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            type__in=["IN", "OUT", "ADJ+", "ADJ-", "REV"]
                        ),
                        name="inventory_movement_type_valid",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            quantity__gt=0,
                            previous_stock__gte=0,
                            final_stock__gte=0,
                            unit_cost__gte=0,
                        ),
                        name="inventory_movement_quantities_valid",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="InventoryCount",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("OPEN", "Em andamento"),
                            ("DONE", "Concluído"),
                            ("CANCELLED", "Cancelado"),
                        ],
                        default="OPEN",
                        max_length=10,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="InventoryItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "system_quantity",
                    models.DecimalField(decimal_places=3, max_digits=12),
                ),
                (
                    "counted_quantity",
                    models.DecimalField(decimal_places=3, max_digits=12),
                ),
                (
                    "inventory",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="inventory.inventorycount",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="inventory.product",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("inventory", "product"),
                        name=(
                            "inventory_inventoryitem_inventory_product_uniq"
                        ),
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            system_quantity__gte=0,
                            counted_quantity__gte=0,
                        ),
                        name=(
                            "inventory_inventoryitem_quantities_nonnegative"
                        ),
                    ),
                ]
            },
        ),
    ]
