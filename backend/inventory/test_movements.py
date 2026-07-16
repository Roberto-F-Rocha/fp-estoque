from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from .models import UserProfile, Category, Product, Movement
from rest_framework import status
from decimal import Decimal
from pprint import pprint

User = get_user_model()

class MovementTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            "admin-movements",
            password="AdminMovements123",
            is_staff=True,
            is_superuser=True,
        )

        UserProfile.objects.create(
            user=self.admin,
            full_name="Administrador",
            role=UserProfile.ADMIN,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_movement_list_endpoint_returns_success(self):
        response = self.client.get("/api/movements/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_filter_by_type_returns_only_matching_movements(self):
        category = Category.objects.create(
            name="Bebidas",
        )

        product = Product.objects.create(
            code="MOV-001",
            name="Produto Teste",
            category=category,
            cost_price=Decimal("5.00"),
            sale_price=Decimal("8.00"),
            minimum_stock=Decimal("1.000"),
            maximum_stock=Decimal("100.000"),
        )

        Movement.objects.create(
            product=product,
            type=Movement.ENTRY,
            quantity=Decimal("2"),
            previous_stock=Decimal("10"),
            final_stock=Decimal("8"),
            user=self.admin,
        )

        response = self.client.get(
            "/api/movements/?type=ENTRY"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

        self.assertEqual(
            len(response.data["results"]),
            1,
        )

        self.assertEqual(
            response.data["results"][0]["type"],
            Movement.ENTRY,
        )