from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import UserProfile


User = get_user_model()


class LocalitiesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin-localidades",
            password="AdminLocalidades123!",
            is_staff=True,
            is_superuser=True,
        )
        UserProfile.objects.create(
            user=self.user,
            full_name="Administrador de localidades",
            role=UserProfile.ADMIN,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @staticmethod
    def response(payload):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = payload
        return response

    def test_loads_ibge_cities_and_filters_by_state(self):
        states_payload = [
            {"id": 24, "sigla": "RN", "nome": "Rio Grande do Norte"},
            {"id": 25, "sigla": "PB", "nome": "Paraíba"},
        ]
        cities_payload = [
            {
                "id": 2408102,
                "nome": "Natal",
                "microrregiao": {"mesorregiao": {"UF": {"sigla": "RN"}}},
            },
            {
                "id": 2507507,
                "nome": "João Pessoa",
                "microrregiao": {"mesorregiao": {"UF": {"sigla": "PB"}}},
            },
        ]

        with TemporaryDirectory() as temporary_directory:
            with (
                override_settings(DATA_DIR=Path(temporary_directory)),
                patch(
                    "inventory.views.localities.requests.get",
                    side_effect=[
                        self.response(states_payload),
                        self.response(cities_payload),
                    ],
                ) as request_get,
            ):
                response = self.client.get("/api/localidades/")
                filtered = self.client.get("/api/localidades/", {"state": "RN"})

            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["source"], "IBGE")
            self.assertEqual(len(response.data["states"]), 2)
            self.assertEqual(len(response.data["cities"]), 2)
            self.assertEqual(response.data["cities"][0]["name"], "João Pessoa")
            self.assertEqual(response.data["cities"][1]["state"], "RN")

            self.assertEqual(filtered.status_code, 200, filtered.data)
            self.assertEqual(filtered.data["cities"], [
                {"id": 2408102, "name": "Natal", "state": "RN"},
            ])
            self.assertEqual(request_get.call_count, 2)
            self.assertTrue((Path(temporary_directory) / "localidades_ibge.json").is_file())

    def test_uses_cached_cities_when_ibge_is_unavailable(self):
        with TemporaryDirectory() as temporary_directory:
            cache_file = Path(temporary_directory) / "localidades_ibge.json"
            cache_file.write_text(
                '{"updated_at":"2000-01-01T00:00:00+00:00","source":"IBGE","states":[{"id":24,"name":"Rio Grande do Norte","code":"RN"}],"cities":[{"id":2408102,"name":"Natal","state":"RN"}]}',
                encoding="utf-8",
            )

            with (
                override_settings(DATA_DIR=Path(temporary_directory)),
                patch(
                    "inventory.views.localities.requests.get",
                    side_effect=OSError("sem conexão"),
                ),
            ):
                response = self.client.get("/api/localidades/")

            self.assertEqual(response.status_code, 200, response.data)
            self.assertTrue(response.data["stale"])
            self.assertEqual(response.data["cities"][0]["name"], "Natal")
