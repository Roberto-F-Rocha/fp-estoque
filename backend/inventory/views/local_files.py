import os
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from ..permissions import IsInventoryUser
from ..services import audit

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_IMAGE_SIZE = 8 * 1024 * 1024


@api_view(["POST"])
@permission_classes([IsInventoryUser])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def upload_product_image(request):
    image = request.FILES.get("image")
    if not image:
        return Response({"image": "Envie um arquivo de imagem."}, status=400)

    if image.size > MAX_IMAGE_SIZE:
        return Response({"image": "A imagem deve possuir no máximo 8 MB."}, status=400)

    content_type = (image.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        return Response(
            {"image": "Formato não permitido. Utilize JPG, PNG ou WEBP."},
            status=400,
        )

    original_extension = os.path.splitext(image.name)[1].lower()
    extension = original_extension if original_extension in {".jpg", ".jpeg", ".png", ".webp"} else ALLOWED_IMAGE_TYPES[content_type]
    if extension == ".jpeg":
        extension = ".jpg"

    relative_path = f"products/{uuid4().hex}{extension}"
    saved_path = default_storage.save(relative_path, image)
    public_url = request.build_absolute_uri(f"{settings.MEDIA_URL}{saved_path}")

    audit(
        request.user,
        "UPLOAD_IMAGE",
        description="Imagem de produto salva no armazenamento local.",
        metadata={"path": saved_path},
    )
    return Response({"path": saved_path, "url": public_url}, status=201)
