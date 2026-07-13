from rest_framework import serializers

from ..models import Alert, AuditLog, InventoryCount, InventoryItem, Notification, SystemSetting

class InventoryItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)
    difference = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)

    class Meta:
        model = InventoryItem
        fields = "__all__"
        read_only_fields = ["inventory", "system_quantity", "adjusted", "adjustment_movement", "created_at", "updated_at"]


class InventorySerializer(serializers.ModelSerializer):
    items = InventoryItemSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    divergences_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = InventoryCount
        fields = "__all__"
        read_only_fields = ["number", "user", "completed_at", "created_at", "updated_at"]


class AlertSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    lot_number = serializers.CharField(source="lot.number", read_only=True)
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    level_display = serializers.CharField(source="get_level_display", read_only=True)

    class Meta:
        model = Alert
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "resolved_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ["user", "created_at", "updated_at", "read_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = AuditLog
        fields = "__all__"
        read_only_fields = ["created_at"]


class SystemSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSetting
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]
