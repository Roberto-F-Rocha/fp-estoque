from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Category, Movement, Product, UserProfile

User = get_user_model()


class ReportXlsxTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "admin-xlsx",
            password="AdminXlsx123!",
            is_superuser=True,
            is_staff=True,
        )
        UserProfile.objects.create(
            user=self.user,
            full_name="Administrador XLSX",
            role=UserProfile.ADMIN,
        )
        category = Category.objects.create(name="Bebidas")
        product = Product.objects.create(
            code="XLSX001",
            name="Produto para relatório",
            category=category,
            cost_price="10.00",
            sale_price="20.00",
        )
        Movement.register(
            product=product,
            type=Movement.ADJUSTMENT_IN,
            quantity=5,
            user=self.user,
            reason="Carga de teste",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_exports_valid_xlsx_package(self):
        response = self.client.get(
            "/api/reports/export.xlsx",
            {
                "type": "daily_movements",
                "date": timezone.localdate().isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertTrue(response.content.startswith(b"PK"))
        self.assertIn(".xlsx", response["Content-Disposition"])
