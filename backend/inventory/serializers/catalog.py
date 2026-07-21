from uuid import uuid4

from rest_framework import serializers

from ..models import Category, Lot, Product, ProductSupplier, Supplier
from ..validators import validate_document


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class SupplierSerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(read_only=True)
    entries_count = serializers.IntegerField(read_only=True)
    entries_value = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True, allow_null=True)
    last_entry = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta:
        model = Supplier
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]

    def validate_document(self, value):
        return validate_document(value) if value else value


class ProductSupplierSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)

    class Meta:
        model = ProductSupplier
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    low_stock = serializers.BooleanField(read_only=True)
    stock_value = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    volume_label = serializers.CharField(read_only=True)
    lots_count = serializers.IntegerField(read_only=True)
    supplier_links = ProductSupplierSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ["stock", "created_at", "updated_at"]
        extra_kwargs = {
            "code": {"required": False, "allow_blank": True},
            "sku": {"required": False, "allow_blank": True, "allow_null": True},
            "barcode": {"required": False, "allow_blank": True, "allow_null": True},
            "location": {"required": False, "allow_blank": True},
            "image_url": {"required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        minimum = attrs.get("minimum_stock", getattr(self.instance, "minimum_stock", 0))
        maximum = attrs.get("maximum_stock", getattr(self.instance, "maximum_stock", 0))
        volume = attrs.get("volume", getattr(self.instance, "volume", 1))
        if maximum and maximum < minimum:
            raise serializers.ValidationError({"maximum_stock": "O estoque máximo não pode ser menor que o mínimo."})
        if volume is None or volume <= 0:
            raise serializers.ValidationError({"volume": "O volume deve ser maior que zero."})
        return attrs

    def create(self, validated_data):
        if not validated_data.get("code"):
            validated_data["code"] = self._automatic_code()
        validated_data.setdefault("unit", "UN")
        validated_data.setdefault("package_quantity", 1)
        return super().create(validated_data)

    @staticmethod
    def _automatic_code():
        while True:
            code = f"PROD-{uuid4().hex[:8].upper()}"
            if not Product.objects.filter(code=code).exists():
                return code


class LotSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    status = serializers.CharField(read_only=True)
    expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Lot
        fields = "__all__"
        read_only_fields = ["quantity", "received_quantity", "created_at", "updated_at"]
