import mimetypes
import os
from datetime import datetime, timedelta
from uuid import uuid4

import requests
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import Alert, Lot, Movement, Product, SystemSetting
from ..permissions import IsInventoryUser
from ..reports import REPORT_TYPES, build_report_data, csv_response, pdf_response
from ..serializers import AlertSerializer, MovementSerializer
from ..services import audit

User = get_user_model()


@api_view(["GET"])
@permission_classes([IsInventoryUser])
def dashboard(request):
    period = request.GET.get("period", "today")
    today = timezone.localdate()
    if period == "7d":
        start = today - timedelta(days=6)
    elif period == "month":
        start = today.replace(day=1)
    elif period == "custom":
        start = datetime.strptime(request.GET.get("start_date", str(today)), "%Y-%m-%d").date()
    else:
        start = today
    end = datetime.strptime(request.GET.get("end_date", str(today)), "%Y-%m-%d").date() if period == "custom" else today

    movements = Movement.objects.filter(created_at__date__range=(start, end))
    entries = movements.filter(type__in=Movement.INCREASE_TYPES)
    outputs = movements.filter(type__in=Movement.DECREASE_TYPES)
    chart_qs = movements.annotate(day=TruncDate("created_at")).values("day").annotate(
        entries=Sum("quantity", filter=Q(type__in=Movement.INCREASE_TYPES)),
        outputs=Sum("quantity", filter=Q(type__in=Movement.DECREASE_TYPES)),
        total=Count("id"),
    ).order_by("day")

    category_stock = Product.objects.filter(active=True).values("category__name").annotate(
        quantity=Sum("stock"), value=Sum(F("stock") * F("cost_price"))
    ).order_by("category__name")
    top_stock = Product.objects.filter(active=True).order_by("-stock")[:8]
    top_outputs = Product.objects.filter(active=True).annotate(
        output_qty=Sum("movements__quantity", filter=Q(movements__type__in=Movement.DECREASE_TYPES, movements__created_at__date__range=(start, end)))
    ).order_by("-output_qty")[:8]
    expiry_days = SystemSetting.get_int("expiration_alert_days", 30)

    return Response({
        "period": {"start": start, "end": end},
        "products": Product.objects.filter(active=True).count(),
        "stock_items": Product.objects.filter(active=True).aggregate(v=Sum("stock"))["v"] or 0,
        "low_stock": Product.objects.filter(active=True, stock__lte=F("minimum_stock"), stock__gt=0).count(),
        "out_of_stock": Product.objects.filter(active=True, stock=0).count(),
        "expiring": Lot.objects.filter(quantity__gt=0, expiration_date__gte=today, expiration_date__lte=today + timedelta(days=expiry_days)).count(),
        "expired": Lot.objects.filter(quantity__gt=0, expiration_date__lt=today).count(),
        "inventory_value": Product.objects.filter(active=True).aggregate(v=Sum(F("stock") * F("cost_price")))["v"] or 0,
        "entries_period": entries.aggregate(v=Sum("quantity"))["v"] or 0,
        "outputs_period": outputs.aggregate(v=Sum("quantity"))["v"] or 0,
        "recent": MovementSerializer(Movement.objects.select_related("product", "product__category", "user", "lot")[:10], many=True).data,
        "alerts": AlertSerializer(Alert.objects.filter(active=True).select_related("product", "lot")[:10], many=True).data,
        "charts": {
            "movements": [{"date": row["day"], "entries": row["entries"] or 0, "outputs": row["outputs"] or 0, "total": row["total"]} for row in chart_qs],
            "category_stock": list(category_stock),
            "top_stock": [{"name": p.name, "value": p.stock} for p in top_stock],
            "top_outputs": [{"name": p.name, "value": p.output_qty or 0} for p in top_outputs],
        },
    })


@api_view(["GET"])
@permission_classes([IsInventoryUser])
def report_catalog(request):
    return Response([{"id": key, "name": value} for key, value in REPORT_TYPES.items()])


@api_view(["GET"])
@permission_classes([IsInventoryUser])
def report_preview(request):
    report_type = request.GET.get("type", "daily_movements")
    try:
        return Response(build_report_data(report_type, request.GET, request.user))
    except (ValueError, DjangoValidationError) as exc:
        return Response({"detail": str(exc)}, status=400)


@api_view(["GET"])
@permission_classes([IsInventoryUser])
def report_export(request, export_format):
    report_type = request.GET.get("type", "daily_movements")
    try:
        data = build_report_data(report_type, request.GET, request.user)
    except (ValueError, DjangoValidationError) as exc:
        return Response({"detail": str(exc)}, status=400)
    audit(request.user, "EXPORT_REPORT", description=f"Relatório {report_type} exportado em {export_format.upper()}.", metadata=dict(request.GET))
    return csv_response(data) if export_format == "csv" else pdf_response(data)


@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password(request):
    identifier = (request.data.get("identifier") or "").strip()
    user = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier), is_active=True).first()
    response = {"detail": "Caso o usuário exista, as instruções de recuperação foram geradas."}
    if user and os.getenv("DEBUG", "true").lower() == "true":
        response["uid"] = urlsafe_base64_encode(force_bytes(user.pk))
        response["token"] = default_token_generator.make_token(user)
        response["development_note"] = "Ambiente de desenvolvimento: use o UID e o token na redefinição de senha."
    return Response(response)


@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):
    try:
        uid = force_str(urlsafe_base64_decode(request.data.get("uid", "")))
        user = User.objects.get(pk=uid, is_active=True)
    except Exception:
        return Response({"detail": "Link de recuperação inválido."}, status=400)
    token = request.data.get("token", "")
    password = request.data.get("password", "")
    if not default_token_generator.check_token(user, token):
        return Response({"detail": "Token inválido ou expirado."}, status=400)
    if len(password) < 8:
        return Response({"password": "Informe uma senha com pelo menos 8 caracteres."}, status=400)
    user.set_password(password)
    user.save(update_fields=["password"])
    audit(user, "SELF_RESET_PASSWORD", user, "Senha recuperada pelo próprio usuário.")
    return Response({"detail": "Senha redefinida com sucesso."})


@api_view(["POST"])
@permission_classes([IsInventoryUser])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def upload_product_image(request):
    image = request.FILES.get("image")
    if not image:
        return Response({"image": "Envie um arquivo de imagem."}, status=400)
    project_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "product-images")
    if not project_url or not service_key:
        return Response({"detail": "Configure SUPABASE_SERVICE_ROLE_KEY e SUPABASE_STORAGE_BUCKET no ambiente para habilitar uploads."}, status=503)
    extension = os.path.splitext(image.name)[1].lower() or ".bin"
    path = f"products/{uuid4().hex}{extension}"
    content_type = image.content_type or mimetypes.guess_type(image.name)[0] or "application/octet-stream"
    url = f"{project_url}/storage/v1/object/{bucket}/{path}"
    response = requests.post(url, data=image.read(), headers={"Authorization": f"Bearer {service_key}", "apikey": service_key, "Content-Type": content_type, "x-upsert": "false"}, timeout=30)
    if response.status_code >= 300:
        return Response({"detail": "Falha ao enviar imagem ao Supabase Storage.", "storage_error": response.text[:300]}, status=502)
    public_url = f"{project_url}/storage/v1/object/public/{bucket}/{path}"
    audit(request.user, "UPLOAD_IMAGE", description="Imagem de produto enviada ao Supabase Storage.", metadata={"path": path})
    return Response({"path": path, "url": public_url}, status=201)
