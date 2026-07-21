from .alerts import AlertViewSet, AuditLogViewSet, NotificationViewSet, SystemSettingViewSet
from .catalog import CategoryViewSet, LotViewSet, ProductViewSet, SupplierViewSet, UserViewSet
from .dashboard import dashboard
from .desktop import desktop_setup, desktop_status, health
from .documents import MovementViewSet, StockAdjustmentViewSet, StockEntryViewSet, StockOutputViewSet
from .inventories import InventoryViewSet
from .local_auth import forgot_password, reset_password
from .local_files import upload_product_image
from .local_reports import report_file, report_open_local, report_save_local
from .misc import report_catalog, report_export, report_preview
from .report_history import report_download_history
from .reporting import report_xlsx_export

__all__ = [
    name
    for name in globals()
    if name.endswith("ViewSet")
    or name
    in {
        "dashboard",
        "desktop_setup",
        "desktop_status",
        "forgot_password",
        "health",
        "report_catalog",
        "report_download_history",
        "report_export",
        "report_file",
        "report_open_local",
        "report_preview",
        "report_save_local",
        "report_xlsx_export",
        "reset_password",
        "upload_product_image",
    }
]
