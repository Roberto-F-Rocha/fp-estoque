import os
import re
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..permissions import IsInventoryUser
from ..reports import build_report_data, pdf_response, xlsx_response
from ..services import audit


REPORT_FORMATS = {
    "pdf": (".pdf", pdf_response),
    "xlsx": (".xlsx", xlsx_response),
}


def _safe_filename(report_type: str, extension: str):
    name = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(report_type or "relatorio")).strip("-")
    if not name:
        name = "relatorio"
    return f"{name}-{timezone.localdate().isoformat()}{extension}"


def _downloads_directory():
    configured = os.getenv("FP_EXPORT_DIR", "").strip()
    directory = Path(configured).expanduser().resolve() if configured else Path.home() / "Downloads"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _available_destination(filename: str):
    directory = _downloads_directory()
    candidate = directory / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1
    while True:
        alternative = directory / f"{stem} ({counter}){suffix}"
        if not alternative.exists():
            return alternative
        counter += 1


def _response_bytes(response):
    try:
        if getattr(response, "streaming", False):
            return b"".join(response.streaming_content)
        return bytes(response.content)
    finally:
        response.close()


@api_view(["POST"])
@permission_classes([IsInventoryUser])
def report_save_local(request):
    if not settings.DESKTOP_MODE:
        return Response(
            {"detail": "O salvamento local está disponível somente na versão desktop."},
            status=404,
        )

    export_format = str(request.data.get("format") or "").lower().strip()
    format_config = REPORT_FORMATS.get(export_format)
    if not format_config:
        return Response({"format": "Escolha PDF ou Excel (XLSX)."}, status=400)

    raw_filters = request.data.get("filters") or {}
    if not isinstance(raw_filters, dict):
        return Response({"filters": "Os filtros enviados são inválidos."}, status=400)

    filters = {str(key): value for key, value in raw_filters.items()}
    report_type = str(filters.get("type") or "daily_movements")

    try:
        data = build_report_data(report_type, filters, request.user)
    except (ValueError, DjangoValidationError) as exc:
        return Response({"detail": str(exc)}, status=400)

    extension, response_factory = format_config
    generated_response = response_factory(data)
    content = _response_bytes(generated_response)
    if not content:
        return Response({"detail": "O relatório foi gerado sem conteúdo."}, status=500)

    destination = _available_destination(_safe_filename(report_type, extension))
    temporary = destination.with_name(f".{destination.name}.tmp")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)

    audit(
        request.user,
        "EXPORT_REPORT",
        description=f"Relatório {report_type} salvo localmente em {export_format.upper()}.",
        metadata={"path": str(destination), **filters},
    )

    return Response(
        {
            "detail": "Relatório salvo com sucesso.",
            "path": str(destination),
            "filename": destination.name,
            "format": export_format,
        },
        status=201,
    )
