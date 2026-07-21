from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AlertViewSet,
    AuditLogViewSet,
    CategoryViewSet,
    InventoryViewSet,
    LotViewSet,
    MovementViewSet,
    NotificationViewSet,
    ProductViewSet,
    StockAdjustmentViewSet,
    StockEntryViewSet,
    StockOutputViewSet,
    SupplierViewSet,
    SystemSettingViewSet,
    UserViewSet,
    brazil_localities,
    dashboard,
    desktop_setup,
    desktop_status,
    forgot_password,
    health,
    report_catalog,
    report_download_history,
    report_export,
    report_file,
    report_open_local,
    report_preview,
    report_save_local,
    report_xlsx_export,
    reset_password,
    upload_product_image,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="users")
router.register("categories", CategoryViewSet)
router.register("suppliers", SupplierViewSet, basename="suppliers")
router.register("products", ProductViewSet, basename="products")
router.register("lots", LotViewSet)
router.register("entries", StockEntryViewSet)
router.register("outputs", StockOutputViewSet)
router.register("movements", MovementViewSet)
router.register("adjustments", StockAdjustmentViewSet)
router.register("inventories", InventoryViewSet)
router.register("alerts", AlertViewSet)
router.register("notifications", NotificationViewSet, basename="notifications")
router.register("audit-logs", AuditLogViewSet)
router.register("settings", SystemSettingViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("health/", health, name="health"),
    path("desktop/status/", desktop_status, name="desktop-status"),
    path("desktop/setup/", desktop_setup, name="desktop-setup"),
    path("localidades/", brazil_localities, name="brazil-localities"),
    path("dashboard/", dashboard, name="dashboard"),
    path("auth/forgot-password/", forgot_password, name="forgot-password"),
    path("auth/reset-password/", reset_password, name="reset-password"),
    path("uploads/product-image/", upload_product_image, name="product-image-upload"),
    path("reports/", report_catalog, name="report-catalog"),
    path("reports/preview/", report_preview, name="report-preview"),
    path("reports/save-local/", report_save_local, name="report-save-local"),
    path("reports/history/", report_download_history, name="report-download-history"),
    path("reports/history/<int:audit_id>/open/", report_open_local, name="report-open-local"),
    path("reports/history/<int:audit_id>/file/", report_file, name="report-file"),
    path("reports/export.pdf", report_export, {"export_format": "pdf"}, name="report-pdf"),
    path("reports/export.xlsx", report_xlsx_export, name="report-xlsx"),
    path("reports/export.csv", report_export, {"export_format": "csv"}, name="report-csv"),
    path("reports/daily.pdf", report_export, {"export_format": "pdf"}, name="daily-report-pdf"),
    path("reports/daily.xlsx", report_xlsx_export, name="daily-report-xlsx"),
    path("reports/daily.csv", report_export, {"export_format": "csv"}, name="daily-report-csv"),
]
