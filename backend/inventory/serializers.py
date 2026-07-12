from rest_framework import serializers
from .models import Category,Supplier,Product,Lot,Movement,InventoryCount,InventoryItem
class CategorySerializer(serializers.ModelSerializer):
    class Meta: model=Category; fields='__all__'
class SupplierSerializer(serializers.ModelSerializer):
    class Meta: model=Supplier; fields='__all__'
class ProductSerializer(serializers.ModelSerializer):
    low_stock=serializers.BooleanField(read_only=True)
    class Meta: model=Product; fields='__all__'; read_only_fields=['stock']
class LotSerializer(serializers.ModelSerializer):
    product_name=serializers.CharField(source='product.name',read_only=True)
    class Meta: model=Lot; fields='__all__'; read_only_fields=['quantity']
class MovementSerializer(serializers.ModelSerializer):
    product_name=serializers.CharField(source='product.name',read_only=True); user_name=serializers.CharField(source='user.username',read_only=True)
    class Meta: model=Movement; fields='__all__'; read_only_fields=['previous_stock','final_stock','user','reversed']
    def create(self,validated_data):
        return Movement.register(user=self.context['request'].user,**validated_data)
class InventoryItemSerializer(serializers.ModelSerializer):
    difference=serializers.DecimalField(max_digits=12,decimal_places=3,read_only=True)
    class Meta: model=InventoryItem; fields='__all__'; read_only_fields=['inventory','system_quantity']
class InventorySerializer(serializers.ModelSerializer):
    items=InventoryItemSerializer(many=True,read_only=True)
    class Meta: model=InventoryCount; fields='__all__'; read_only_fields=['user']
