from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import create_app

API_PREFIX = "/api/v1"


class AnalyticsServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.tempdir.name) / "analytics.db"
        self.previous_env = {
            "DATABASE_URL": os.getenv("DATABASE_URL"),
            "INTERNAL_API_KEY": os.getenv("INTERNAL_API_KEY"),
            "SURVEY_SERVICE_URL": os.getenv("SURVEY_SERVICE_URL"),
        }

        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_path.as_posix()}"
        os.environ["INTERNAL_API_KEY"] = "test-internal-token"
        os.environ["SURVEY_SERVICE_URL"] = "http://survey-service.test"

        self.client_manager = TestClient(create_app())
        self.client = self.client_manager.__enter__()

    def tearDown(self) -> None:
        self.client_manager.__exit__(None, None, None)
        self.tempdir.cleanup()

        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_basic_analytics_returns_count(self) -> None:
        with patch("app.routers.analytics.fetch_answer_count", return_value=7):
            response = self.client.get(f"{API_PREFIX}/surveys/1/analytics/basic")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.data(response), {"survey_id": 1, "answers_count": 7})

    def test_answer_created_requires_internal_token(self) -> None:
        response = self.client.post(
            f"{API_PREFIX}/internal-events:answer-created",
            json=self._event_payload(answer_id=1),
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.error_message(response), "Unauthorized")

    def test_answer_created_updates_stats_and_awards_first_achievement(self) -> None:
        response = self._post_event(
            answer_id=1,
            user_id=10,
            question_id=101,
            survey_id=501,
            idempotency_key="idem-1",
        )

        self.assertEqual(response.status_code, 200)
        body = self.data(response)
        self.assertEqual(body["status"], "processed")
        self.assertEqual(body["answer_count"], 1)
        self.assertEqual(
            [achievement["id"] for achievement in body["awarded_achievements"]],
            [1],
        )

        detailed = self.client.get(f"{API_PREFIX}/surveys/501/analytics/detailed")
        self.assertEqual(detailed.status_code, 200)
        self.assertEqual(
            self.data(detailed),
            {
                "survey_id": 501,
                "total_submissions": 1,
                "questions": [
                    {
                        "question_id": 101,
                        "submission_count": 1,
                        "percentage": 100.0,
                    }
                ],
            },
        )

        achievements = self.client.get(f"{API_PREFIX}/users/10/achievements")
        self.assertEqual(achievements.status_code, 200)
        self.assertEqual(
            [achievement["id"] for achievement in self.data(achievements)["achievements"]],
            [1],
        )

    def test_idempotency_and_detailed_export_and_advanced_analytics(self) -> None:
        first_response = self._post_event(
            answer_id=2,
            user_id=20,
            question_id=202,
            survey_id=502,
            idempotency_key="idem-2",
            duration_seconds=10,
        )
        second_response = self._post_event(
            answer_id=2,
            user_id=20,
            question_id=202,
            survey_id=502,
            idempotency_key="idem-2",
            duration_seconds=10,
        )
        self._post_event(
            answer_id=3,
            user_id=21,
            question_id=203,
            survey_id=502,
            idempotency_key="idem-3",
            duration_seconds=20,
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(self.data(second_response), self.data(first_response))

        detailed = self.client.get(f"{API_PREFIX}/surveys/502/analytics/detailed")
        json_export = self.client.get(f"{API_PREFIX}/surveys/502/analytics/export")
        advanced = self.client.get(f"{API_PREFIX}/surveys/502/analytics/advanced")

        self.assertEqual(detailed.status_code, 200)
        self.assertEqual(self.data(detailed)["total_submissions"], 2)
        self.assertEqual(json_export.status_code, 200)
        self.assertEqual(self.data(json_export)["survey_id"], 502)
        self.assertEqual(advanced.status_code, 200)
        self.assertEqual(self.data(advanced)["average_completion_seconds"], 15.0)

    def test_submission_created_updates_multiple_question_stats_once(self) -> None:
        response = self._post_submission_event(
            submission_id=1,
            user_id=60,
            survey_id=506,
            question_ids=[601, 602],
            idempotency_key="submission-idem-1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.data(response)["question_counts"],
            [
                {"question_id": 601, "submission_count": 1},
                {"question_id": 602, "submission_count": 1},
            ],
        )

    def test_complex_achievements_and_notifications(self) -> None:
        for index in range(1, 51):
            self._post_event(
                answer_id=index,
                user_id=70,
                question_id=700 + index,
                survey_id=7000 + index,
                idempotency_key=f"worker-idem-{index}",
                category=f"category-{index % 5}",
            )

        for _ in range(50):
            follower_response = self.client.post(
                f"{API_PREFIX}/internal-events:follower-created",
                json={"user_id": 70},
                headers={"X-Internal-Token": "test-internal-token"},
            )
            self.assertEqual(follower_response.status_code, 200)

        achievements = self.client.get(f"{API_PREFIX}/users/70/achievements")
        notifications = self.client.get(f"{API_PREFIX}/users/70/notifications")

        achievement_names = [
            item["name"] for item in self.data(achievements)["achievements"]
        ]
        self.assertIn("Hard worker", achievement_names)
        self.assertIn("Explorer", achievement_names)
        self.assertIn("Celebrity", achievement_names)
        self.assertEqual(notifications.status_code, 200)
        self.assertTrue(self.data(notifications)["notifications"])

    def test_failed_processing_marks_operation_as_failed(self) -> None:
        with patch(
            "app.services.event_service.increment_question_stats",
            side_effect=RuntimeError("boom"),
        ):
            response = self._post_event(
                answer_id=9999,
                user_id=50,
                question_id=501,
                survey_id=505,
                idempotency_key="idem-failed",
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.error_message(response), "Failed to process event")

        processed_row = self._fetchone(
            "SELECT status FROM processed_events WHERE answer_id = ?",
            ("9999",),
        )
        idempotency_row = self._fetchone(
            "SELECT status FROM idempotency_keys WHERE key = ?",
            ("idem-failed",),
        )
        self.assertEqual(processed_row["status"], "failed")
        self.assertEqual(idempotency_row["status"], "failed")

    def _post_event(
        self,
        *,
        answer_id: int,
        user_id: int,
        question_id: int,
        survey_id: int,
        idempotency_key: str,
        category: str | None = None,
        duration_seconds: float | None = None,
    ):
        return self.client.post(
            f"{API_PREFIX}/internal-events:answer-created",
            json=self._event_payload(
                answer_id=answer_id,
                user_id=user_id,
                question_id=question_id,
                survey_id=survey_id,
                category=category,
                duration_seconds=duration_seconds,
            ),
            headers={
                "X-Internal-Token": "test-internal-token",
                "Idempotency-Key": idempotency_key,
            },
        )

    def _post_submission_event(
        self,
        *,
        submission_id: int,
        user_id: int,
        survey_id: int,
        question_ids: list[int],
        idempotency_key: str,
    ):
        return self.client.post(
            f"{API_PREFIX}/internal-events:submission-created",
            json={
                "user_id": user_id,
                "submission_id": submission_id,
                "survey_id": survey_id,
                "question_ids": question_ids,
            },
            headers={
                "X-Internal-Token": "test-internal-token",
                "Idempotency-Key": idempotency_key,
            },
        )

    def _event_payload(
        self,
        *,
        answer_id: int,
        user_id: int = 1,
        question_id: int = 1,
        survey_id: int = 1,
        category: str | None = None,
        duration_seconds: float | None = None,
    ) -> dict[str, object]:
        return {
            "user_id": user_id,
            "answer_id": answer_id,
            "question_id": question_id,
            "survey_id": survey_id,
            "category": category,
            "duration_seconds": duration_seconds,
        }

    def data(self, response):
        return response.json()["data"]

    def error_message(self, response) -> str:
        return response.json()["errors"][0]["message"]

    def _fetchone(self, query: str, params: tuple[object, ...]) -> sqlite3.Row:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            row = connection.execute(query, params).fetchone()
        finally:
            connection.close()

        self.assertIsNotNone(row)
        return row

    def _fetchval(self, query: str) -> int:
        connection = sqlite3.connect(self.database_path)
        try:
            value = connection.execute(query).fetchone()[0]
        finally:
            connection.close()
        return int(value)
