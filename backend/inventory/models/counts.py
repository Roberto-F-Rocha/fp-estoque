from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from .base import NumberedDocument, TimeStamped
from .catalog import Category, Product
from .movement import Movement

class InventoryCount(NumberedDocument):
    OPEN = "OPEN"
    WAITING = "WAITING"
    DONE = "DONE"
    CANCELLED = "CANCELLED"
    STATUS = [
        (OPEN, "Em andamento"),
        (WAITING, "Aguardando confirmação"),
        (DONE, "Concluído"),
        (CANCELLED, "Cancelado"),
    ]

    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default=OPEN)
    notes = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, null=True, blank=True, related_name="inventories")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="inventories")

    class Meta:
        ordering = ["-started_at"]

    def save(self, *args, **kwargs):
        self.ensure_number("INV")
        super().save(*args, **kwargs)

    def conclude(self, user):
        if self.status not in {self.OPEN, self.WAITING}:
            raise ValidationError("Este inventário não pode ser concluído.")
        with transaction.atomic():
            for item in self.items.select_related("product"):
                diff = item.difference
                if diff:
                    movement = Movement.register(
                        product=item.product,
                        type=Movement.INVENTORY if diff > 0 else Movement.ADJUSTMENT_OUT,
                        quantity=abs(diff),
                        user=user,
                        reason=f"Divergência do inventário {self.number}",
                        notes=item.justification,
                        document=self.number,
                    )
                    item.adjustment_movement = movement
                    item.adjusted = True
                    item.save(update_fields=["adjustment_movement", "adjusted"])
            self.status = self.DONE
            self.completed_at = timezone.now()
            self.save(update_fields=["status", "completed_at", "updated_at"])
        return self


class InventoryItem(TimeStamped):
    inventory = models.ForeignKey(InventoryCount, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="inventory_items")
    system_quantity = models.DecimalField(max_digits=14, decimal_places=3)
    counted_quantity = models.DecimalField(max_digits=14, decimal_places=3)
    justification = models.TextField(blank=True)
    adjusted = models.BooleanField(default=False)
    adjustment_movement = models.OneToOneField(Movement, on_delete=models.PROTECT, null=True, blank=True, related_name="inventory_item")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["inventory", "product"], name="inventory_inventoryitem_inventory_product_uniq"),
            models.CheckConstraint(
                condition=Q(system_quantity__gte=0, counted_quantity__gte=0),
                name="inventory_inventoryitem_quantities_nonnegative",
            ),
        ]

    @property
    def difference(self):
        return self.counted_quantity - self.system_quantity


