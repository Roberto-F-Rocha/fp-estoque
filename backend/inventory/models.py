from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models, transaction


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStamped):
    name = models.CharField(max_length=100, unique=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Supplier(TimeStamped):
    name = models.CharField(max_length=180)
    document = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
    )
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(TimeStamped):
    code = models.CharField(max_length=50, unique=True)
    barcode = models.CharField(
        max_length=80,
        unique=True,
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    brand = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=20, default="UN")
    cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    sale_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    stock = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
    )
    minimum_stock = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
    )
    location = models.CharField(max_length=100, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    cost_price__gte=0,
                    sale_price__gte=0,
                    stock__gte=0,
                    minimum_stock__gte=0,
                ),
                name="inventory_product_nonnegative_values",
            )
        ]
        indexes = [models.Index(fields=["name"], name="inv_product_name_idx")]

    @property
    def low_stock(self):
        return self.stock <= self.minimum_stock

    def __str__(self):
        return self.name


class Lot(TimeStamped):
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="lots",
    )
    number = models.CharField(max_length=80)
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
    )
    expiration_date = models.DateField(null=True, blank=True)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        unique_together = ("product", "number")
        ordering = ["expiration_date", "created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=0),
                name="inventory_lot_quantity_nonnegative",
            )
        ]
        indexes = [
            models.Index(
                fields=["expiration_date"],
                name="inv_lot_expiration_idx",
            )
        ]

    def __str__(self):
        return f"{self.product} — lote {self.number}"


class Movement(TimeStamped):
    IN = "IN"
    OUT = "OUT"
    ADJUSTMENT_IN = "ADJ+"
    ADJUSTMENT_OUT = "ADJ-"
    REVERSAL = "REV"

    TYPES = [
        (IN, "Entrada"),
        (OUT, "Saída"),
        (ADJUSTMENT_IN, "Ajuste positivo"),
        (ADJUSTMENT_OUT, "Ajuste negativo"),
        (REVERSAL, "Estorno"),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="movements",
    )
    lot = models.ForeignKey(
        Lot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    type = models.CharField(max_length=5, choices=TYPES)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    previous_stock = models.DecimalField(max_digits=12, decimal_places=3)
    final_stock = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    reason = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    reversed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
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
        ]
        indexes = [
            models.Index(
                fields=["-created_at"],
                name="inv_movement_created_idx",
            ),
            models.Index(fields=["type"], name="inv_movement_type_idx"),
        ]

    @classmethod
    def register(
        cls,
        *,
        product,
        type,
        quantity,
        user,
        lot=None,
        reason="",
        notes="",
        unit_cost=None,
    ):
        if type not in dict(cls.TYPES):
            raise ValidationError("Tipo de movimentação inválido.")

        quantity = abs(quantity)
        if quantity <= 0:
            raise ValidationError("A quantidade deve ser maior que zero.")

        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=product.pk)
            previous = product.stock
            is_increase = type in (cls.IN, cls.ADJUSTMENT_IN, cls.REVERSAL)
            delta = quantity if is_increase else -quantity

            if previous + delta < 0:
                raise ValidationError("Estoque insuficiente para esta saída.")

            if lot:
                lot = Lot.objects.select_for_update().get(pk=lot.pk)
                if lot.product_id != product.pk:
                    raise ValidationError(
                        "O lote informado não pertence ao produto selecionado."
                    )
                if lot.quantity + delta < 0:
                    raise ValidationError("Quantidade insuficiente no lote.")
                lot.quantity += delta
                lot.save(update_fields=["quantity", "updated_at"])

            product.stock = previous + delta
            product.save(update_fields=["stock", "updated_at"])

            return cls.objects.create(
                product=product,
                lot=lot,
                type=type,
                quantity=quantity,
                previous_stock=previous,
                final_stock=product.stock,
                unit_cost=(
                    unit_cost if unit_cost is not None else product.cost_price
                ),
                reason=reason,
                notes=notes,
                user=user,
            )


class InventoryCount(TimeStamped):
    STATUS = [
        ("OPEN", "Em andamento"),
        ("DONE", "Concluído"),
        ("CANCELLED", "Cancelado"),
    ]

    status = models.CharField(max_length=10, choices=STATUS, default="OPEN")
    notes = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        ordering = ["-created_at"]


class InventoryItem(models.Model):
    inventory = models.ForeignKey(
        InventoryCount,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    system_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    counted_quantity = models.DecimalField(max_digits=12, decimal_places=3)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["inventory", "product"],
                name="inventory_inventoryitem_inventory_product_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    system_quantity__gte=0,
                    counted_quantity__gte=0,
                ),
                name="inventory_inventoryitem_quantities_nonnegative",
            ),
        ]

    @property
    def difference(self):
        return self.counted_quantity - self.system_quantity
