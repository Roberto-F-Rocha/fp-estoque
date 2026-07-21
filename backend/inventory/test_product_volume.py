from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Category, Product, UserProfile


User = get_user_model()


class ProductVolumeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin-volume",
            password="AdminVolume123!",
            is_staff=True,
            is_superuser=True,
        )
        UserProfile.objects.create(
            user=self.user,
            full_name="Administrador de produtos",
            role=UserProfile.ADMIN,
        )
        self.category = Category.objects.create(name="Bebidas em volume")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_creates_product_without_manual_codes_and_formats_milliliters(self):
        response = self.client.post(
            "/api/products/",
            {
                "name": "Cachaça Tradicional",
                "category": self.category.id,
                "package_type": "Garrafa de vidro",
                "volume": "965",
                "volume_unit": "ML",
                "cost_price": "22.00",
                "sale_price": "186.00",
                "minimum_stock": "2",
                "maximum_stock": "30",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        product = Product.objects.get(pk=response.data["id"])
        self.assertTrue(product.code.startswith("PROD-"))
        self.assertEqual(product.sku, None)
        self.assertEqual(product.barcode, None)
        self.assertEqual(product.unit, "UN")
        self.assertEqual(product.package_quantity, Decimal("1"))
        self.assertEqual(product.volume, Decimal("965"))
        self.assertEqual(product.volume_unit, "ML")
        self.assertEqual(product.volume_label, "965 mL")
        self.assertEqual(response.data["volume_label"], "965 mL")

    def test_formats_liters_and_rejects_zero_volume(self):
        product = Product.objects.create(
            code="VOLUME-001",
            name="Refrigerante",
            category=self.category,
            volume=Decimal("1"),
            volume_unit="L",
        )
        self.assertEqual(product.volume_label, "1 L")

        response = self.client.post(
            "/api/products/",
            {
                "name": "Produto sem volume",
                "category": self.category.id,
                "volume": "0",
                "volume_unit": "ML",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("volume", response.data)
