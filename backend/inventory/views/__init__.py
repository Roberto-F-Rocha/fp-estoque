from .alerts import AlertViewSet, AuditLogViewSet, NotificationViewSet, SystemSettingViewSet
from .catalog import CategoryViewSet, LotViewSet, ProductViewSet, SupplierViewSet, UserViewSet
from .dashboard import dashboard
from .desktop import desktop_setup, desktop_status, health
from .documents import MovementViewSet, StockAdjustmentViewSet, StockEntryViewSet, StockOutputViewSet
from .inventories import InventoryViewSet
from .local_files import upload_product_image
from .misc import forgot_password, report_catalog, report_export, report_preview, reset_password
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
        "report_export",
        "report_preview",
        "report_xlsx_export",
        "reset_password",
        "upload_product_image",
    }
]
