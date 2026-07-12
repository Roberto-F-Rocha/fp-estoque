from datetime import date,datetime,time,timedelta
from io import BytesIO
from django.db.models import Sum,Count,F,Q
from django.http import FileResponse
from django.utils import timezone
from rest_framework import viewsets,status
from rest_framework.decorators import action,api_view,permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from reportlab.lib.pagesizes import A4,landscape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from .models import Category,Supplier,Product,Lot,Movement,InventoryCount,InventoryItem
from .serializers import *

class BaseVS(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
class CategoryVS(BaseVS): queryset=Category.objects.all(); serializer_class=CategorySerializer; search_fields=['name']; ordering_fields=['name','created_at']
class SupplierVS(BaseVS): queryset=Supplier.objects.all(); serializer_class=SupplierSerializer; search_fields=['name','document','email']; ordering_fields=['name','created_at']
class ProductVS(BaseVS):
    queryset=Product.objects.select_related('category','supplier').all(); serializer_class=ProductSerializer; filterset_fields=['category','supplier','active']; search_fields=['name','code','barcode','brand']; ordering_fields=['name','stock','cost_price','created_at']
    @action(detail=False)
    def low_stock(self,request):
        qs=self.get_queryset().filter(stock__lte=F('minimum_stock'))
        return Response(self.get_serializer(qs,many=True).data)
class LotVS(BaseVS): queryset=Lot.objects.select_related('product','supplier').all(); serializer_class=LotSerializer; filterset_fields=['product','supplier']; search_fields=['number','product__name']
class MovementVS(BaseVS):
    http_method_names=['get','post','head','options']; queryset=Movement.objects.select_related('product','lot','user').all(); serializer_class=MovementSerializer; filterset_fields=['type','product','user']; search_fields=['product__name','reason','notes']; ordering_fields=['created_at','quantity']
class InventoryVS(BaseVS):
    queryset=InventoryCount.objects.prefetch_related('items').all(); serializer_class=InventorySerializer
    def perform_create(self,serializer): serializer.save(user=self.request.user)
    @action(detail=True,methods=['post'])
    def add_item(self,request,pk=None):
        inv=self.get_object(); product=Product.objects.get(pk=request.data['product']); item=InventoryItem.objects.update_or_create(inventory=inv,product=product,defaults={'system_quantity':product.stock,'counted_quantity':request.data['counted_quantity']})[0]; return Response(InventoryItemSerializer(item).data)
    @action(detail=True,methods=['post'])
    def conclude(self,request,pk=None):
        inv=self.get_object()
        for item in inv.items.select_related('product'):
            diff=item.difference
            if diff: Movement.register(product=item.product,type='ADJ+' if diff>0 else 'ADJ-',quantity=abs(diff),user=request.user,reason=f'Inventário #{inv.pk}')
        inv.status='DONE'; inv.save(update_fields=['status','updated_at']); return Response(self.get_serializer(inv).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    today=timezone.localdate(); qs=Movement.objects.filter(created_at__date=today)
    return Response({'products':Product.objects.filter(active=True).count(),'stock_items':Product.objects.aggregate(v=Sum('stock'))['v'] or 0,'low_stock':Product.objects.filter(stock__lte=F('minimum_stock')).count(),'out_of_stock':Product.objects.filter(stock=0).count(),'inventory_value':Product.objects.aggregate(v=Sum(F('stock')*F('cost_price')))['v'] or 0,'entries_today':qs.filter(type='IN').aggregate(v=Sum('quantity'))['v'] or 0,'outputs_today':qs.filter(type='OUT').aggregate(v=Sum('quantity'))['v'] or 0,'recent':MovementSerializer(Movement.objects.select_related('product','user')[:10],many=True).data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def daily_report(request):
    raw=request.GET.get('date',str(timezone.localdate())); chosen=datetime.strptime(raw,'%Y-%m-%d').date(); qs=Movement.objects.select_related('product','user','lot').filter(created_at__date=chosen).order_by('created_at')
    buf=BytesIO(); doc=SimpleDocTemplate(buf,pagesize=landscape(A4),rightMargin=24,leftMargin=24,topMargin=28,bottomMargin=28); styles=getSampleStyleSheet(); story=[Paragraph('FP DEPÓSITO DE BEBIDAS — RELATÓRIO DIÁRIO DE ESTOQUE',styles['Title']),Paragraph(f'Data: {chosen.strftime("%d/%m/%Y")} | Gerado por: {request.user.username} | Emissão: {timezone.localtime().strftime("%d/%m/%Y %H:%M")}',styles['Normal']),Spacer(1,12)]
    total_in=qs.filter(type__in=['IN','ADJ+','REV']).aggregate(v=Sum('quantity'))['v'] or 0; total_out=qs.filter(type__in=['OUT','ADJ-']).aggregate(v=Sum('quantity'))['v'] or 0
    story += [Paragraph(f'Resumo: {qs.count()} movimentações | Entradas: {total_in} | Saídas: {total_out}',styles['Heading2']),Spacer(1,8)]
    data=[['Horário','Tipo','Produto','Lote','Qtd. anterior','Movimentada','Qtd. final','Custo','Responsável','Motivo']]
    for m in qs: data.append([timezone.localtime(m.created_at).strftime('%H:%M'),m.get_type_display(),m.product.name,m.lot.number if m.lot else '-',str(m.previous_stock),str(m.quantity),str(m.final_stock),f'R$ {m.unit_cost:.2f}',m.user.username,m.reason or '-'])
    if len(data)==1: data.append(['-','Sem movimentações nesta data','-','-','-','-','-','-','-','-'])
    table=Table(data,repeatRows=1,colWidths=[42,65,120,65,62,62,62,55,70,115]); table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#F5B400')),('TEXTCOLOR',(0,0),(-1,0),colors.black),('GRID',(0,0),(-1,-1),.4,colors.grey),('FONTSIZE',(0,0),(-1,-1),7),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F7F7F7')])]))
    story.append(table); doc.build(story); buf.seek(0); return FileResponse(buf,as_attachment=True,filename=f'relatorio-estoque-{chosen}.pdf')
