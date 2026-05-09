from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import create_app


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
            response = self.client.get("/analytics/surveys/1/basic")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"survey_id": 1, "answers_count": 7})

    def test_answer_created_requires_internal_token(self) -> None:
        response = self.client.post(
            "/internal/events/answer-created",
            json=self._event_payload(answer_id="answer-1"),
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Unauthorized"})

    def test_answer_created_updates_stats_and_awards_first_achievement(self) -> None:
        response = self._post_event(
            answer_id="answer-1",
            user_id=10,
            question_id=101,
            survey_id=501,
            idempotency_key="idem-1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "processed")
        self.assertEqual(body["answer_count"], 1)
        self.assertEqual(
            [achievement["name"] for achievement in body["awarded_achievements"]],
            ["Первый ответ"],
        )

        detailed = self.client.get("/analytics/surveys/501/detailed")
        self.assertEqual(detailed.status_code, 200)
        self.assertEqual(
            detailed.json(),
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

        achievements = self.client.get("/users/10/achievements")
        self.assertEqual(achievements.status_code, 200)
        self.assertEqual(
            [achievement["name"] for achievement in achievements.json()["achievements"]],
            ["Первый ответ"],
        )

        processed_row = self._fetchone(
            "SELECT status FROM processed_events WHERE answer_id = ?",
            ("answer-1",),
        )
        idempotency_row = self._fetchone(
            "SELECT status FROM idempotency_keys WHERE key = ?",
            ("idem-1",),
        )
        self.assertEqual(processed_row["status"], "completed")
        self.assertEqual(idempotency_row["status"], "completed")

    def test_idempotency_and_deduplication_return_saved_result(self) -> None:
        first_response = self._post_event(
            answer_id="answer-2",
            user_id=20,
            question_id=202,
            survey_id=502,
            idempotency_key="idem-2",
        )
        second_response = self._post_event(
            answer_id="answer-2",
            user_id=20,
            question_id=202,
            survey_id=502,
            idempotency_key="idem-2",
        )
        third_response = self._post_event(
            answer_id="answer-2",
            user_id=20,
            question_id=202,
            survey_id=502,
            idempotency_key="idem-2b",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(third_response.status_code, 200)
        self.assertEqual(second_response.json(), first_response.json())
        self.assertEqual(third_response.json(), first_response.json())

        detailed = self.client.get("/analytics/surveys/502/detailed")
        self.assertEqual(detailed.json()["total_submissions"], 1)
        self.assertEqual(
            self._fetchval("SELECT COUNT(*) FROM processed_events"),
            1,
        )
        self.assertEqual(
            self._fetchval("SELECT COUNT(*) FROM idempotency_keys"),
            2,
        )

    def test_detailed_analytics_and_csv_export(self) -> None:
        self._post_event(
            answer_id="answer-3",
            user_id=30,
            question_id=301,
            survey_id=503,
            idempotency_key="idem-3",
        )
        self._post_event(
            answer_id="answer-4",
            user_id=30,
            question_id=302,
            survey_id=503,
            idempotency_key="idem-4",
        )

        detailed = self.client.get("/analytics/surveys/503/detailed")
        self.assertEqual(detailed.status_code, 200)
        self.assertEqual(
            detailed.json(),
            {
                "survey_id": 503,
                "total_submissions": 2,
                "questions": [
                    {
                        "question_id": 301,
                        "submission_count": 1,
                        "percentage": 50.0,
                    },
                    {
                        "question_id": 302,
                        "submission_count": 1,
                        "percentage": 50.0,
                    },
                ],
            },
        )

        export_response = self.client.get("/analytics/surveys/503/export?format=csv")
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("text/csv", export_response.headers["content-type"])
        self.assertIn(
            'attachment; filename="survey_503_analytics.csv"',
            export_response.headers["content-disposition"],
        )

        csv_lines = export_response.text.strip().splitlines()
        self.assertEqual(csv_lines[0], "question_id,submission_count,percentage")
        self.assertEqual(csv_lines[1], "301,1,50.0")
        self.assertEqual(csv_lines[2], "302,1,50.0")

    def test_submission_created_updates_multiple_question_stats_once(self) -> None:
        response = self._post_submission_event(
            submission_id="submission-1",
            user_id=60,
            survey_id=506,
            question_ids=[601, 602],
            idempotency_key="submission-idem-1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "processed")
        self.assertEqual(body["submission_id"], "submission-1")
        self.assertEqual(body["survey_id"], 506)
        self.assertEqual(
            body["question_counts"],
            [
                {"question_id": 601, "submission_count": 1},
                {"question_id": 602, "submission_count": 1},
            ],
        )
        self.assertEqual(len(body["awarded_achievements"]), 1)
        self.assertEqual(body["awarded_achievements"][0]["id"], 1)
        self.assertTrue(body["awarded_achievements"][0]["awarded_at"])

        detailed = self.client.get("/analytics/surveys/506/detailed")
        self.assertEqual(
            detailed.json(),
            {
                "survey_id": 506,
                "total_submissions": 1,
                "questions": [
                    {
                        "question_id": 601,
                        "submission_count": 1,
                        "percentage": 100.0,
                    },
                    {
                        "question_id": 602,
                        "submission_count": 1,
                        "percentage": 100.0,
                    },
                ],
            },
        )

    def test_achievements_are_awarded_for_thresholds_and_distinct_surveys(self) -> None:
        for index in range(1, 11):
            self._post_event(
                answer_id=f"answer-10-{index}",
                user_id=40,
                question_id=401,
                survey_id=504,
                idempotency_key=f"idem-10-{index}",
            )

        for survey_offset in range(1, 5):
            self._post_event(
                answer_id=f"answer-survey-{survey_offset}",
                user_id=40,
                question_id=401 + survey_offset,
                survey_id=504 + survey_offset,
                idempotency_key=f"idem-survey-{survey_offset}",
            )

        for index in range(15, 101):
            self._post_event(
                answer_id=f"answer-100-{index}",
                user_id=40,
                question_id=499,
                survey_id=504,
                idempotency_key=f"idem-100-{index}",
            )

        achievements = self.client.get("/users/40/achievements")
        self.assertEqual(achievements.status_code, 200)
        self.assertEqual(
            [achievement["name"] for achievement in achievements.json()["achievements"]],
            ["Первый ответ", "10 ответов", "Мастер опросов", "100 ответов"],
        )

    def test_failed_processing_marks_operation_as_failed(self) -> None:
        with patch(
            "app.services.event_service.increment_question_stats",
            side_effect=RuntimeError("boom"),
        ):
            response = self._post_event(
                answer_id="answer-failed",
                user_id=50,
                question_id=501,
                survey_id=505,
                idempotency_key="idem-failed",
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Failed to process event"})

        processed_row = self._fetchone(
            "SELECT status FROM processed_events WHERE answer_id = ?",
            ("answer-failed",),
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
        answer_id: str,
        user_id: int,
        question_id: int,
        survey_id: int,
        idempotency_key: str,
    ):
        return self.client.post(
            "/internal/events/answer-created",
            json=self._event_payload(
                answer_id=answer_id,
                user_id=user_id,
                question_id=question_id,
                survey_id=survey_id,
            ),
            headers={
                "X-Internal-Token": "test-internal-token",
                "Idempotency-Key": idempotency_key,
            },
        )

    def _post_submission_event(
        self,
        *,
        submission_id: str,
        user_id: int,
        survey_id: int,
        question_ids: list[int],
        idempotency_key: str,
    ):
        return self.client.post(
            "/internal/events/submission-created",
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
        answer_id: str,
        user_id: int = 1,
        question_id: int = 1,
        survey_id: int = 1,
    ) -> dict[str, object]:
        return {
            "user_id": user_id,
            "answer_id": answer_id,
            "question_id": question_id,
            "survey_id": survey_id,
        }

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
