from __future__ import annotations

import sqlite3
from typing import Any


def increment_question_stat(
    connection: sqlite3.Connection,
    survey_id: int,
    question_id: int,
) -> int:
    connection.execute(
        """
        INSERT INTO question_stats (survey_id, question_id, answer_count)
        VALUES (?, ?, 1)
        ON CONFLICT(survey_id, question_id) DO UPDATE SET
            answer_count = answer_count + 1;
        """,
        (survey_id, question_id),
    )

    row = connection.execute(
        """
        SELECT answer_count
        FROM question_stats
        WHERE survey_id = ? AND question_id = ?;
        """,
        (survey_id, question_id),
    ).fetchone()

    return int(row["answer_count"])


def increment_question_stats(
    connection: sqlite3.Connection,
    survey_id: int,
    question_ids: list[int],
) -> list[dict[str, int]]:
    counts: list[dict[str, int]] = []
    for question_id in question_ids:
        counts.append(
            {
                "question_id": question_id,
                "submission_count": increment_question_stat(
                    connection=connection,
                    survey_id=survey_id,
                    question_id=question_id,
                ),
            }
        )
    return counts


def get_detailed_survey_stats(
    connection: sqlite3.Connection,
    survey_id: int,
) -> dict[str, Any]:
    rows = connection.execute(
        """
        SELECT question_id, answer_count
        FROM question_stats
        WHERE survey_id = ?
        ORDER BY question_id;
        """,
        (survey_id,),
    ).fetchall()

    total_submissions = _count_total_submissions(connection, survey_id)
    questions = []

    for row in rows:
        submission_count = int(row["answer_count"])
        percentage = (
            round((submission_count / total_submissions) * 100, 2)
            if total_submissions
            else 0.0
        )
        questions.append(
            {
                "question_id": int(row["question_id"]),
                "submission_count": submission_count,
                "percentage": percentage,
            }
        )

    return {
        "survey_id": survey_id,
        "total_submissions": total_submissions,
        "questions": questions,
    }


def get_advanced_survey_stats(
    connection: sqlite3.Connection,
    survey_id: int,
) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT
            COUNT(DISTINCT answer_id) AS total_submissions,
            AVG(duration_seconds) AS average_completion_seconds
        FROM processed_events
        WHERE survey_id = ? AND status = 'completed';
        """,
        (survey_id,),
    ).fetchone()
    return {
        "survey_id": survey_id,
        "total_submissions": int(row["total_submissions"] or 0),
        "average_completion_seconds": round(
            float(row["average_completion_seconds"] or 0), 2
        ),
    }


def _count_total_submissions(connection: sqlite3.Connection, survey_id: int) -> int:
    row = connection.execute(
        """
        SELECT COUNT(DISTINCT answer_id) AS total_submissions
        FROM processed_events
        WHERE survey_id = ? AND status = 'completed';
        """,
        (survey_id,),
    ).fetchone()
    if row is None:
        return 0
    return int(row["total_submissions"])
