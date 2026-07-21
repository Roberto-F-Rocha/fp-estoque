from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import UserProfile


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

    def test_saves_pdf_in_local_directory(self):
        with TemporaryDirectory() as temporary_directory:
            export_directory = Path(temporary_directory)
            with patch(
                "inventory.views.local_reports._downloads_directory",
                return_value=export_directory,
            ):
                response = self.client.post(
                    "/api/reports/save-local/",
                    self.payload("pdf"),
                    format="json",
                )

            self.assertEqual(response.status_code, 201)
            destination = Path(response.data["path"])
            self.assertTrue(destination.is_file())
            self.assertEqual(destination.suffix, ".pdf")
            self.assertTrue(destination.read_bytes().startswith(b"%PDF"))

    def test_saves_xlsx_and_avoids_overwriting_existing_file(self):
        with TemporaryDirectory() as temporary_directory:
            export_directory = Path(temporary_directory)
            with patch(
                "inventory.views.local_reports._downloads_directory",
                return_value=export_directory,
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
