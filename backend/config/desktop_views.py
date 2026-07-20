import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse


def _safe_file(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise Http404("Arquivo inválido.") from exc
    if not candidate.is_file():
        raise Http404("Arquivo não encontrado.")
    return candidate


def desktop_index(request):
    index_file = settings.DESKTOP_FRONTEND_DIR / "index.html"
    if not index_file.is_file():
        return HttpResponse(
            "A interface desktop ainda não foi compilada. Execute npm run build:desktop na pasta frontend.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )
    return FileResponse(index_file.open("rb"), content_type="text/html; charset=utf-8")


def desktop_asset(request, asset_path):
    file_path = _safe_file(settings.DESKTOP_FRONTEND_DIR, asset_path)
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    return FileResponse(file_path.open("rb"), content_type=content_type)
