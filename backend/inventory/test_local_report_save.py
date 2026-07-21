from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import AuditLog, UserProfile


User = get_user_model()


@override_settings(DESKTOP_MODE=True)
class LocalReportSaveTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin-local-report",
            password="AdminLocal123!",
            is_staff=True,
            is_superuser=True,
        )
        UserProfile.objects.create(
            user=self.user,
            full_name="Administrador local",
            role=UserProfile.ADMIN,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def payload(self, export_format):
        return {
            "format": export_format,
            "filters": {
                "type": "daily_movements",
                "date": timezone.localdate().isoformat(),
                "start_date": "",
                "end_date": "",
                "product": "",
                "category": "",
                "supplier": "",
                "movement_type": "",
                "user": "",
                "lot": "",
                "stock_status": "",
                "brand": "",
            },
        }

    def test_saves_pdf_records_request_and_opens_file(self):
        with TemporaryDirectory() as temporary_directory:
            export_directory = Path(temporary_directory)
            with (
                patch(
                    "inventory.views.local_reports._downloads_directory",
                    return_value=export_directory,
                ),
                patch(
                    "inventory.views.local_reports._open_file",
                    return_value=(True, ""),
                ) as open_file,
            ):
                response = self.client.post(
                    "/api/reports/save-local/",
                    self.payload("pdf"),
                    format="json",
                )

            self.assertEqual(response.status_code, 201)
            self.assertTrue(response.data["auto_opened"])
            destination = Path(response.data["path"])
            self.assertTrue(destination.is_file())
            self.assertEqual(destination.suffix, ".pdf")
            self.assertTrue(destination.read_bytes().startswith(b"%PDF"))
            open_file.assert_called_once_with(destination)

            audit_log = AuditLog.objects.get(pk=response.data["audit_id"])
            self.assertEqual(audit_log.action, "REPORT_DOWNLOAD")
            self.assertEqual(audit_log.entity, "ReportExport")
            self.assertEqual(audit_log.metadata["status"], "SUCCESS")
            self.assertEqual(audit_log.metadata["format"], "pdf")
            self.assertEqual(audit_log.metadata["path"], str(destination))
            self.assertEqual(audit_log.metadata["open_count"], 1)

    def test_saves_xlsx_and_avoids_overwriting_existing_file(self):
        with TemporaryDirectory() as temporary_directory:
            export_directory = Path(temporary_directory)
            with (
                patch(
                    "inventory.views.local_reports._downloads_directory",
                    return_value=export_directory,
                ),
                patch(
                    "inventory.views.local_reports._open_file",
                    return_value=(True, ""),
                ),
            ):
                first = self.client.post(
                    "/api/reports/save-local/",
                    self.payload("xlsx"),
                    format="json",
                )
                second = self.client.post(
                    "/api/reports/save-local/",
                    self.payload("xlsx"),
                    format="json",
                )

            self.assertEqual(first.status_code, 201)
            self.assertEqual(second.status_code, 201)
            first_path = Path(first.data["path"])
            second_path = Path(second.data["path"])
            self.assertNotEqual(first_path, second_path)
            self.assertTrue(first_path.read_bytes().startswith(b"PK"))
            self.assertTrue(second_path.read_bytes().startswith(b"PK"))

    def test_history_lists_download_and_opens_existing_file(self):
        with TemporaryDirectory() as temporary_directory:
            export_directory = Path(temporary_directory)
            with (
                patch(
                    "inventory.views.local_reports._downloads_directory",
                    return_value=export_directory,
                ),
                patch(
                    "inventory.views.local_reports._open_file",
                    return_value=(True, ""),
                ),
            ):
                created = self.client.post(
                    "/api/reports/save-local/",
                    self.payload("pdf"),
                    format="json",
                )

                history = self.client.get("/api/reports/history/")
                opened = self.client.post(
                    f"/api/reports/history/{created.data['audit_id']}/open/"
                )

            self.assertEqual(history.status_code, 200)
            self.assertEqual(history.data["count"], 1)
            item = history.data["results"][0]
            self.assertEqual(item["status"], "SUCCESS")
            self.assertEqual(item["format"], "PDF")
            self.assertTrue(item["file_exists"])
            self.assertIn("/open/", item["open_url"])
            self.assertIn("/file/", item["file_url"])
            self.assertEqual(opened.status_code, 200)

            refreshed = AuditLog.objects.get(pk=created.data["audit_id"])
            self.assertEqual(refreshed.metadata["open_count"], 2)

    def test_invalid_format_is_preserved_in_history_as_failure(self):
        response = self.client.post(
            "/api/reports/save-local/",
            self.payload("txt"),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        audit_log = AuditLog.objects.get(pk=response.data["audit_id"])
        self.assertEqual(audit_log.metadata["status"], "FAILED")
        self.assertIn("Escolha PDF", audit_log.metadata["error"])

        history = self.client.get("/api/reports/history/?status=FAILED")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.data["count"], 1)
        self.assertEqual(history.data["summary"]["failed"], 1)

    def test_file_endpoint_returns_saved_pdf(self):
        with TemporaryDirectory() as temporary_directory:
            export_directory = Path(temporary_directory)
            with (
                patch(
                    "inventory.views.local_reports._downloads_directory",
                    return_value=export_directory,
                ),
                patch(
                    "inventory.views.local_reports._open_file",
                    return_value=(True, ""),
                ),
            ):
                created = self.client.post(
                    "/api/reports/save-local/",
                    self.payload("pdf"),
                    format="json",
                )
                file_response = self.client.get(
                    f"/api/reports/history/{created.data['audit_id']}/file/"
                )

            self.assertEqual(file_response.status_code, 200)
            self.assertEqual(file_response["Content-Type"], "application/pdf")
            content = b"".join(file_response.streaming_content)
            self.assertTrue(content.startswith(b"%PDF"))
