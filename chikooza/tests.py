from unittest.mock import patch

from django.db.utils import OperationalError
from django.test import SimpleTestCase
from django.urls import reverse


class LivenessTests(SimpleTestCase):
    @patch("chikooza.health.connection")
    def test_liveness_reports_process_status_without_database_access(
        self, database_connection
    ):
        response = self.client.get(reverse("health-live"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        database_connection.cursor.assert_not_called()


class ReadinessTests(SimpleTestCase):
    @patch("chikooza.health.connection")
    def test_readiness_reports_database_status(self, database_connection):
        response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "checks": {"database": "ok"}},
        )
        cursor = database_connection.cursor.return_value.__enter__.return_value
        cursor.execute.assert_called_once_with("SELECT 1")
        cursor.fetchone.assert_called_once_with()

    @patch("chikooza.health.connection")
    def test_health_alias_uses_readiness_check(self, database_connection):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "checks": {"database": "ok"}},
        )
        database_connection.cursor.assert_called_once_with()

    @patch("chikooza.health.connection")
    def test_readiness_returns_503_without_exposing_database_error(
        self, database_connection
    ):
        database_connection.cursor.side_effect = OperationalError(
            "connection details must not be exposed"
        )

        response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"status": "unavailable", "checks": {"database": "unavailable"}},
        )
        self.assertNotIn("connection details", response.content.decode())
        database_connection.cursor.assert_called_once_with()
