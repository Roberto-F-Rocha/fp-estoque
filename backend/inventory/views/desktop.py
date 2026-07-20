from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import UserProfile

User = get_user_model()


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok", "mode": "desktop-local"})


@api_view(["GET"])
@permission_classes([AllowAny])
def desktop_status(request):
    return Response(
        {
            "setup_required": not User.objects.exists(),
            "storage": "SQLite local",
            "database_file": str(settings.DATABASES["default"]["NAME"]),
            "media_directory": str(settings.MEDIA_ROOT),
            "desktop_mode": settings.DESKTOP_MODE,
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def desktop_setup(request):
    if User.objects.exists():
        return Response(
            {"detail": "A configuração inicial já foi concluída."},
            status=409,
        )

    full_name = str(request.data.get("full_name") or "").strip()
    username = str(request.data.get("username") or "").strip()
    email = str(request.data.get("email") or "").strip()
    password = str(request.data.get("password") or "")
    confirmation = str(request.data.get("password_confirmation") or "")

    errors = {}
    if len(full_name) < 3:
        errors["full_name"] = "Informe o nome completo do administrador."
    if len(username) < 3:
        errors["username"] = "Informe um nome de usuário com pelo menos 3 caracteres."
    if password != confirmation:
        errors["password_confirmation"] = "As senhas informadas não coincidem."

    provisional_user = User(username=username, email=email)
    try:
        validate_password(password, provisional_user)
    except ValidationError as exc:
        errors["password"] = list(exc.messages)

    if errors:
        return Response(errors, status=400)

    with transaction.atomic():
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                "full_name": full_name,
                "role": UserProfile.ADMIN,
                "active": True,
            },
        )

    return Response(
        {
            "detail": "Administrador criado. Faça login para acessar o sistema.",
            "username": user.username,
        },
        status=201,
    )
