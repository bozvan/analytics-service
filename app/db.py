from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from app.config import get_settings

ACHIEVEMENT_DEFINITIONS = (
    (
        1,
        "Первый ответ",
        "Пользователь отправил свой первый ответ.",
        "total_answers",
        1,
    ),
    (
        2,
        "10 ответов",
        "Пользователь отправил 10 ответов.",
        "total_answers",
        10,
    ),
    (
        3,
        "100 ответов",
        "Пользователь отправил 100 ответов.",
        "total_answers",
        100,
    ),
    (
        4,
        "Мастер опросов",
        "Пользователь ответил как минимум в 5 разных опросах.",
        "distinct_surveys",
        5,
    ),
)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    database_path = get_settings().database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        database_path,
        detect_types=sqlite3.PARSE_DECLTYPES,
        check_same_thread=False,
        isolation_level=None,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        yield connection
    finally:
        connection.close()


def initialize_database() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS question_stats (
                survey_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                answer_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (survey_id, question_id)
            );

            CREATE INDEX IF NOT EXISTS ix_question_stats_survey_id
            ON question_stats (survey_id);

            CREATE TABLE IF NOT EXISTS processed_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                answer_id TEXT NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                survey_id INTEGER NOT NULL,
                status TEXT NOT NULL
                    CHECK (status IN ('pending', 'completed', 'failed')),
                response_status_code INTEGER,
                response_body TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS ix_processed_events_user_status
            ON processed_events (user_id, status);

            CREATE INDEX IF NOT EXISTS ix_processed_events_user_survey_status
            ON processed_events (user_id, survey_id, status);

            CREATE TABLE IF NOT EXISTS idempotency_keys (
                key TEXT PRIMARY KEY,
                request_hash TEXT NOT NULL,
                answer_id TEXT,
                status TEXT NOT NULL
                    CHECK (status IN ('pending', 'completed', 'failed')),
                response_status_code INTEGER,
                response_body TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS ix_idempotency_keys_answer_id
            ON idempotency_keys (answer_id);

            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                condition_type TEXT NOT NULL,
                condition_value INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS ix_achievements_condition
            ON achievements (condition_type, condition_value);

            CREATE TABLE IF NOT EXISTS user_achievements (
                user_id INTEGER NOT NULL,
                achievement_id INTEGER NOT NULL,
                awarded_at TEXT NOT NULL,
                PRIMARY KEY (user_id, achievement_id),
                FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS ix_user_achievements_user_id
            ON user_achievements (user_id);
            """
        )
        seed_achievements(connection)


def seed_achievements(connection: sqlite3.Connection) -> None:
    for achievement in ACHIEVEMENT_DEFINITIONS:
        connection.execute(
            """
            INSERT INTO achievements (
                id,
                name,
                description,
                condition_type,
                condition_value
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                description = excluded.description,
                condition_type = excluded.condition_type,
                condition_value = excluded.condition_value
            """,
            achievement,
        )
