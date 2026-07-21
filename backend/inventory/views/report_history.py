from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..permissions import IsInventoryUser
from .local_reports import _history_queryset, _serialize_history


@api_view(["GET"])
@permission_classes([IsInventoryUser])
def report_download_history(request):
    try:
        page = max(int(request.GET.get("page") or 1), 1)
        page_size = min(max(int(request.GET.get("page_size") or 20), 1), 100)
    except ValueError:
        page, page_size = 1, 20

    records = [_serialize_history(log) for log in _history_queryset(request)]
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
