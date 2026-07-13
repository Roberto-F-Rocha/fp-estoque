from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    Category,
    InventoryCount,
    InventoryItem,
    Lot,
    Movement,
    Product,
    Supplier,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ["stock"]


class LotSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = Lot
        fields = "__all__"
        read_only_fields = ["quantity"]


class MovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Movement
        fields = "__all__"
        read_only_fields = [
            "previous_stock",
            "final_stock",
            "user",
            "reversed",
        ]

    def validate(self, attrs):
        product = attrs.get("product")
        lot = attrs.get("lot")
        if lot and product and lot.product_id != product.id:
            raise serializers.ValidationError(
                {"lot": "O lote não pertence ao produto selecionado."}
            )
        return attrs

    def create(self, validated_data):
        try:
            return Movement.register(
                user=self.context["request"].user,
                **validated_data,
            )
        except DjangoValidationError as exc:
            if hasattr(exc, "message_dict"):
                detail = exc.message_dict
            else:
                detail = exc.messages
            raise serializers.ValidationError(detail) from exc


class InventoryItemSerializer(serializers.ModelSerializer):
    difference = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    class Meta:
        model = InventoryItem
        fields = "__all__"
        read_only_fields = ["inventory", "system_quantity"]


class InventorySerializer(serializers.ModelSerializer):
    items = InventoryItemSerializer(many=True, read_only=True)

    class Meta:
        model = InventoryCount
        fields = "__all__"
        read_only_fields = ["user"]
