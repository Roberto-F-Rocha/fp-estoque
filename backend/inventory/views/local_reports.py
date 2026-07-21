import mimetypes
import os
import re
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..models import AuditLog
from ..permissions import IsInventoryUser
from ..reports import REPORT_TYPES, build_report_data, pdf_response, xlsx_response
from ..services import audit


REPORT_FORMATS = {
    "pdf": (".pdf", pdf_response),
    "xlsx": (".xlsx", xlsx_response),
}
REPORT_AUDIT_ACTION = "REPORT_DOWNLOAD"
LEGACY_REPORT_ACTION = "EXPORT_REPORT"
REPORT_FILTER_KEYS = {
    "type",
    "date",
    "start_date",
    "end_date",
    "product",
    "category",
    "supplier",
    "movement_type",
    "user",
    "lot",
    "stock_status",
    "brand",
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


def _is_admin(user):
    if getattr(user, "is_superuser", False):
        return True
    profile = getattr(user, "inventory_profile", None)
    return getattr(profile, "role", "") == "ADMIN"


def _update_audit(log, status, description, **metadata):
    current = dict(log.metadata or {})
    current.update(metadata)
    current["status"] = status
    current["updated_at"] = timezone.localtime().isoformat()
    log.entity = "ReportExport"
    log.description = description
    log.metadata = current
    log.save(update_fields=["entity", "description", "metadata"])


def _report_request_log(user, export_format, filters):
    report_type = str(filters.get("type") or "daily_movements")
    log = audit(
        user,
        REPORT_AUDIT_ACTION,
        description=f"Solicitação de relatório {report_type} em {export_format.upper() or 'formato não informado'}.",
        metadata={
            "status": "REQUESTED",
            "format": export_format,
            "report_type": report_type,
            "report_name": REPORT_TYPES.get(report_type, report_type),
            "filters": filters,
            "requested_at": timezone.localtime().isoformat(),
        },
    )
    log.entity = "ReportExport"
    log.save(update_fields=["entity"])
    return log


def _open_file(path: Path):
    if getattr(settings, "RUNNING_TESTS", False):
        return False, "A abertura automática é ignorada durante os testes."

    try:
        if os.name == "nt":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)], close_fds=True)
        else:
            subprocess.Popen(["xdg-open", str(path)], close_fds=True)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _legacy_filters(metadata):
    nested = metadata.get("filters")
    if isinstance(nested, dict):
        return nested
    return {key: metadata.get(key) for key in REPORT_FILTER_KEYS if metadata.get(key) not in (None, "")}


def _format_from_metadata(metadata):
    export_format = str(metadata.get("format") or "").lower()
    if export_format in REPORT_FORMATS:
        return export_format
    suffix = Path(str(metadata.get("path") or "")).suffix.lower()
    return "xlsx" if suffix == ".xlsx" else "pdf" if suffix == ".pdf" else ""


def _status_from_log(log, metadata, file_exists):
    status = str(metadata.get("status") or "").upper()
    if status:
        return status
    if log.action == LEGACY_REPORT_ACTION:
        return "SUCCESS" if file_exists else "FILE_MISSING"
    return "UNKNOWN"


def _serialize_history(log):
    metadata = dict(log.metadata or {})
    raw_path = str(metadata.get("path") or "")
    path = Path(raw_path) if raw_path else None
    file_exists = bool(path and path.is_file())
    report_type = str(metadata.get("report_type") or metadata.get("type") or "daily_movements")
    export_format = _format_from_metadata(metadata)
    filters = _legacy_filters(metadata)
    status = _status_from_log(log, metadata, file_exists)

    return {
        "id": log.id,
        "created_at": log.created_at,
        "user_id": log.user_id,
        "user_name": (
            getattr(getattr(log.user, "inventory_profile", None), "full_name", "")
            or getattr(log.user, "username", "")
            or "Usuário removido"
        ),
        "report_type": report_type,
        "report_name": metadata.get("report_name") or REPORT_TYPES.get(report_type, report_type),
        "format": export_format.upper() if export_format else "-",
        "status": status,
        "status_label": {
            "REQUESTED": "Solicitado",
            "PROCESSING": "Processando",
            "SUCCESS": "Concluído",
            "FAILED": "Falhou",
            "FILE_MISSING": "Arquivo não encontrado",
            "UNKNOWN": "Não identificado",
        }.get(status, status.title()),
        "filename": metadata.get("filename") or (path.name if path else ""),
        "path": raw_path,
        "file_exists": file_exists,
        "file_size": metadata.get("file_size") or (path.stat().st_size if file_exists else 0),
        "filters": filters,
        "error": metadata.get("error") or "",
        "auto_opened": bool(metadata.get("auto_opened")),
        "auto_open_error": metadata.get("auto_open_error") or "",
        "open_count": int(metadata.get("open_count") or 0),
        "last_opened_at": metadata.get("last_opened_at") or metadata.get("opened_at") or "",
        "open_url": f"/api/reports/history/{log.id}/open/" if file_exists else "",
        "file_url": f"/api/reports/history/{log.id}/file/" if file_exists else "",
    }


def _history_queryset(request):
    queryset = AuditLog.objects.filter(
        action__in=[REPORT_AUDIT_ACTION, LEGACY_REPORT_ACTION]
    ).select_related("user", "user__inventory_profile").order_by("-created_at")
    if not _is_admin(request.user):
        queryset = queryset.filter(user=request.user)
    return queryset


def _get_history_log(request, audit_id):
    try:
        log = _history_queryset(request).get(pk=audit_id)
    except AuditLog.DoesNotExist as exc:
        raise Http404("Registro de download não encontrado.") from exc
    return log


def _validated_history_path(log):
    metadata = dict(log.metadata or {})
    raw_path = str(metadata.get("path") or "").strip()
    if not raw_path:
        raise Http404("Este registro não possui um arquivo associado.")

    candidate = Path(raw_path).expanduser().resolve()
    allowed_root = Path(metadata.get("export_root") or _downloads_directory()).expanduser().resolve()
    try:
        candidate.relative_to(allowed_root)
    except ValueError as exc:
        raise Http404("O arquivo está fora da pasta autorizada de relatórios.") from exc

    if candidate.suffix.lower() not in {".pdf", ".xlsx"} or not candidate.is_file():
        raise Http404("O arquivo do relatório não foi encontrado.")
    return candidate


@api_view(["POST"])
@permission_classes([IsInventoryUser])
def report_save_local(request):
    export_format = str(request.data.get("format") or "").lower().strip()
    raw_filters = request.data.get("filters") or {}
    filters = (
        {str(key): value for key, value in raw_filters.items()}
        if isinstance(raw_filters, dict)
        else {}
    )
    request_log = _report_request_log(request.user, export_format, filters)

    if not settings.DESKTOP_MODE:
        message = "O salvamento local está disponível somente na versão desktop."
        _update_audit(request_log, "FAILED", message, error=message)
        return Response({"detail": message, "audit_id": request_log.id}, status=404)

    format_config = REPORT_FORMATS.get(export_format)
    if not format_config:
        message = "Escolha PDF ou Excel (XLSX)."
        _update_audit(request_log, "FAILED", message, error=message)
        return Response({"format": message, "audit_id": request_log.id}, status=400)

    if not isinstance(raw_filters, dict):
        message = "Os filtros enviados são inválidos."
        _update_audit(request_log, "FAILED", message, error=message)
        return Response({"filters": message, "audit_id": request_log.id}, status=400)

    report_type = str(filters.get("type") or "daily_movements")
    _update_audit(
        request_log,
        "PROCESSING",
        f"Gerando relatório {REPORT_TYPES.get(report_type, report_type)} em {export_format.upper()}.",
    )

    try:
        data = build_report_data(report_type, filters, request.user)
        extension, response_factory = format_config
        generated_response = response_factory(data)
        content = _response_bytes(generated_response)
        if not content:
            raise RuntimeError("O relatório foi gerado sem conteúdo.")

        export_root = _downloads_directory()
        destination = _available_destination(_safe_filename(report_type, extension))
        temporary = destination.with_name(f".{destination.name}.tmp")
        try:
            temporary.write_bytes(content)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

        opened, open_error = _open_file(destination)
        opened_at = timezone.localtime().isoformat() if opened else ""
        _update_audit(
            request_log,
            "SUCCESS",
            f"Relatório {REPORT_TYPES.get(report_type, report_type)} salvo em {export_format.upper()}.",
            report_type=report_type,
            report_name=REPORT_TYPES.get(report_type, report_type),
            format=export_format,
            filters=filters,
            path=str(destination),
            filename=destination.name,
            export_root=str(export_root),
            file_size=len(content),
            completed_at=timezone.localtime().isoformat(),
            auto_opened=opened,
            auto_open_error=open_error,
            open_count=1 if opened else 0,
            last_opened_at=opened_at,
        )

        detail = "Relatório salvo e aberto automaticamente."
        if not opened:
            detail = "Relatório salvo, mas não foi possível abri-lo automaticamente."

        return Response(
            {
                "detail": detail,
                "path": str(destination),
                "filename": destination.name,
                "format": export_format,
                "audit_id": request_log.id,
                "auto_opened": opened,
                "auto_open_error": open_error,
                "open_url": f"/api/reports/history/{request_log.id}/open/",
                "file_url": f"/api/reports/history/{request_log.id}/file/",
            },
            status=201,
        )
    except (ValueError, DjangoValidationError) as exc:
        message = str(exc)
        _update_audit(request_log, "FAILED", "Falha ao validar o relatório solicitado.", error=message)
        return Response({"detail": message, "audit_id": request_log.id}, status=400)
    except Exception as exc:
        message = str(exc) or "Não foi possível gerar o relatório."
        _update_audit(request_log, "FAILED", "Falha durante a geração do relatório.", error=message)
        return Response({"detail": message, "audit_id": request_log.id}, status=500)


@api_view(["GET"])
@permission_classes([IsInventoryUser])
def report_download_history(request):
    try:
        page = max(int(request.GET.get("page") or 1), 1)
        page_size = min(max(int(request.GET.get("page_size") or 20), 1), 100)
    except ValueError:
        page, page_size = 1, 20

    records = [_serialize_history(log) for log in _history_queryset(request)[:2000]]
    status_filter = str(request.GET.get("status") or "").upper().strip()
    format_filter = str(request.GET.get("format") or "").upper().strip()
    search = str(request.GET.get("search") or "").strip().lower()

    if status_filter:
        records = [record for record in records if record["status"] == status_filter]
    if format_filter:
        records = [record for record in records if record["format"] == format_filter]
    if search:
        records = [
            record
            for record in records
            if search in " ".join(
                [
                    record["user_name"],
                    record["report_name"],
                    record["filename"],
                    record["path"],
                    record["error"],
                ]
            ).lower()
        ]

    count = len(records)
    start = (page - 1) * page_size
    end = start + page_size
    results = records[start:end]
    summary = {
        "total": count,
        "success": sum(1 for record in records if record["status"] == "SUCCESS"),
        "failed": sum(1 for record in records if record["status"] == "FAILED"),
        "pdf": sum(1 for record in records if record["format"] == "PDF"),
        "xlsx": sum(1 for record in records if record["format"] == "XLSX"),
    }
    return Response(
        {
            "count": count,
            "page": page,
            "page_size": page_size,
            "results": results,
            "summary": summary,
        }
    )


@api_view(["POST"])
@permission_classes([IsInventoryUser])
def report_open_local(request, audit_id):
    log = _get_history_log(request, audit_id)
    path = _validated_history_path(log)
    opened, error = _open_file(path)

    metadata = dict(log.metadata or {})
    metadata["open_count"] = int(metadata.get("open_count") or 0) + (1 if opened else 0)
    metadata["last_opened_at"] = timezone.localtime().isoformat() if opened else metadata.get("last_opened_at", "")
    metadata["last_open_error"] = error
    log.metadata = metadata
    log.save(update_fields=["metadata"])

    audit(
        request.user,
        "REPORT_FILE_OPEN",
        log,
        description=f"Arquivo de relatório {'aberto' if opened else 'não aberto'}: {path.name}.",
        metadata={"path": str(path), "success": opened, "error": error},
    )

    if not opened:
        return Response(
            {"detail": "Não foi possível abrir o arquivo no aplicativo padrão.", "error": error},
            status=500,
        )
    return Response({"detail": "Arquivo aberto no aplicativo padrão.", "path": str(path)})


@api_view(["GET"])
@permission_classes([IsInventoryUser])
def report_file(request, audit_id):
    log = _get_history_log(request, audit_id)
    path = _validated_history_path(log)
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(
        path.open("rb"),
        as_attachment=False,
        filename=path.name,
        content_type=content_type,
    )
