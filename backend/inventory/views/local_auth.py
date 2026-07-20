from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Q
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..services import audit

User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password(request):
    identifier = str(request.data.get("identifier") or "").strip()
    user = User.objects.filter(
        Q(username__iexact=identifier) | Q(email__iexact=identifier),
        is_active=True,
    ).first()

    if not user:
        return Response(
            {"detail": "Usuário não encontrado nesta máquina."},
            status=404,
        )

    return Response(
        {
            "detail": "Recuperação gerada localmente.",
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):
    try:
        uid = force_str(urlsafe_base64_decode(request.data.get("uid", "")))
        user = User.objects.get(pk=uid, is_active=True)
    except Exception:
        return Response({"detail": "Recuperação inválida."}, status=400)

    token = str(request.data.get("token") or "")
    password = str(request.data.get("password") or "")
    if not default_token_generator.check_token(user, token):
        return Response({"detail": "Token inválido ou expirado."}, status=400)
    if len(password) < 8:
        return Response(
            {"password": "Informe uma senha com pelo menos 8 caracteres."},
            status=400,
        )

    user.set_password(password)
    user.save(update_fields=["password"])
    audit(user, "SELF_RESET_PASSWORD", user, "Senha redefinida no aplicativo local.")
    return Response({"detail": "Senha redefinida com sucesso."})
