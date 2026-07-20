import base64
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import UserProfile

User = get_user_model()

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2nWQAAAAASUVORK5CYII="
)


class DesktopSetupTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_first_run_creates_local_administrator(self):
        status_response = self.client.get("/api/desktop/status/")
        self.assertEqual(status_response.status_code, 200)
        self.assertTrue(status_response.data["setup_required"])
        self.assertEqual(status_response.data["storage"], "SQLite local")

        setup_response = self.client.post(
            "/api/desktop/setup/",
            {
                "full_name": "Administrador Local",
                "username": "admin-local",
                "email": "admin@local.test",
                "password": "SenhaLocal123!",
                "password_confirmation": "SenhaLocal123!",
            },
            format="json",
        )
        self.assertEqual(setup_response.status_code, 201)
        user = User.objects.get(username="admin-local")
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.inventory_profile.role, UserProfile.ADMIN)

        next_status = self.client.get("/api/desktop/status/")
        self.assertFalse(next_status.data["setup_required"])

    def test_setup_cannot_run_twice(self):
        user = User.objects.create_superuser("existing-admin", password="Existing123!")
        UserProfile.objects.update_or_create(
            user=user,
            defaults={"full_name": "Administrador", "role": UserProfile.ADMIN},
        )

        response = self.client.post(
            "/api/desktop/setup/",
            {
                "full_name": "Outro Administrador",
                "username": "outro",
                "password": "OutraSenha123!",
                "password_confirmation": "OutraSenha123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 409)


class LocalImageStorageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("operator", password="Operator123!")
        UserProfile.objects.update_or_create(
            user=self.user,
            defaults={
                "full_name": "Operador Local",
                "role": UserProfile.OPERATOR,
                "active": True,
            },
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_product_image_is_saved_to_local_media_directory(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with override_settings(MEDIA_ROOT=Path(temporary_directory), MEDIA_URL="/media/"):
                image = SimpleUploadedFile("produto.png", TINY_PNG, content_type="image/png")
                response = self.client.post(
                    "/api/uploads/product-image/",
                    {"image": image},
                    format="multipart",
                )

                self.assertEqual(response.status_code, 201)
                self.assertTrue(response.data["path"].startswith("products/"))
                self.assertIn("/media/products/", response.data["url"])
                self.assertTrue((Path(temporary_directory) / response.data["path"]).is_file())


class DesktopFrontendTests(TestCase):
    def test_compiled_frontend_is_served_inside_local_window(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "assets").mkdir()
            (root / "index.html").write_text("<html><body>FP Estoque Desktop</body></html>", encoding="utf-8")
            (root / "assets" / "app.js").write_text("console.log('desktop');", encoding="utf-8")

            with override_settings(DESKTOP_FRONTEND_DIR=root):
                index_response = self.client.get("/")
                self.assertEqual(index_response.status_code, 200)
                self.assertIn(b"FP Estoque Desktop", b"".join(index_response.streaming_content))

                asset_response = self.client.get("/desktop/assets/app.js")
                self.assertEqual(asset_response.status_code, 200)
                self.assertIn(b"console.log", b"".join(asset_response.streaming_content))
