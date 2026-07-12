from django.contrib import admin
from .models import *
admin.site.register([Category,Supplier,Product,Lot,Movement,InventoryCount,InventoryItem])
