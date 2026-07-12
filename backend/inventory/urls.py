from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import *
r=DefaultRouter(); r.register('categories',CategoryVS); r.register('suppliers',SupplierVS); r.register('products',ProductVS); r.register('lots',LotVS); r.register('movements',MovementVS); r.register('inventories',InventoryVS)
urlpatterns=[path('',include(r.urls)),path('dashboard/',dashboard),path('reports/daily.pdf',daily_report)]
