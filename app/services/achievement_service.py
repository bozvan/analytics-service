from __future__ import annotations

import sqlite3

from app.db import utcnow


def award_achievements(
    connection: sqlite3.Connection,
    user_id: int,
    answer_id: str,
) -> list[dict[str, object]]:
    total_answers = _count_answers(connection, user_id, answer_id)
    distinct_surveys = _count_distinct_surveys(connection, user_id, answer_id)
    distinct_categories = _count_distinct_categories(connection, user_id, answer_id)
    followers = _count_followers(connection, user_id)

    achievements = connection.execute(
        """
        SELECT id, name, description, condition_type, condition_value
        FROM achievements
        ORDER BY id;
        """
    ).fetchall()

    awarded: list[dict[str, object]] = []

    for achievement in achievements:
        if not _condition_met(
            condition_type=str(achievement["condition_type"]),
            condition_value=int(achievement["condition_value"]),
            total_answers=total_answers,
            distinct_surveys=distinct_surveys,
            distinct_categories=distinct_categories,
            followers=followers,
        ):
            continue

        awarded_at = utcnow()
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO user_achievements (
                user_id,
                achievement_id,
                awarded_at
            )
            VALUES (?, ?, ?);
            """,
            (user_id, int(achievement["id"]), awarded_at),
        )

        if cursor.rowcount:
            awarded.append(
                {
                    "id": int(achievement["id"]),
                    "name": str(achievement["name"]),
                    "description": str(achievement["description"]),
                    "awarded_at": awarded_at,
                }
            )

    return awarded


def increment_followers_and_award(
    connection: sqlite3.Connection,
    user_id: int,
) -> list[dict[str, object]]:
    connection.execute(
        """
        INSERT INTO follower_counts (user_id, followers_count)
        VALUES (?, 1)
        ON CONFLICT(user_id) DO UPDATE SET followers_count = followers_count + 1;
        """,
        (user_id,),
    )
    return _award_by_metrics(
        connection=connection,
        user_id=user_id,
        total_answers=_count_answers(connection, user_id, ""),
        distinct_surveys=_count_distinct_surveys(connection, user_id, ""),
        distinct_categories=_count_distinct_categories(connection, user_id, ""),
        followers=_count_followers(connection, user_id),
    )


def list_user_achievements(
    connection: sqlite3.Connection,
    user_id: int,
) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT
            a.id,
            a.name,
            a.description,
            ua.awarded_at
        FROM user_achievements AS ua
        JOIN achievements AS a ON a.id = ua.achievement_id
        WHERE ua.user_id = ?
        ORDER BY ua.awarded_at, a.id;
        """,
        (user_id,),
    ).fetchall()

    return [
        {
            "id": int(row["id"]),
            "name": str(row["name"]),
            "description": str(row["description"]),
            "awarded_at": str(row["awarded_at"]),
        }
        for row in rows
    ]


def _count_answers(
    connection: sqlite3.Connection,
    user_id: int,
    answer_id: str,
) -> int:
    row = connection.execute(
        """
        SELECT COUNT(*) AS total_answers
        FROM processed_events
        WHERE user_id = ? AND (status = 'completed' OR answer_id = ?);
        """,
        (user_id, answer_id),
    ).fetchone()
    return int(row["total_answers"])


def _count_distinct_surveys(
    connection: sqlite3.Connection,
    user_id: int,
    answer_id: str,
) -> int:
    row = connection.execute(
        """
        SELECT COUNT(DISTINCT survey_id) AS total_surveys
        FROM processed_events
        WHERE user_id = ? AND (status = 'completed' OR answer_id = ?);
        """,
        (user_id, answer_id),
    ).fetchone()
    return int(row["total_surveys"])


def _count_distinct_categories(
    connection: sqlite3.Connection,
    user_id: int,
    answer_id: str,
) -> int:
    row = connection.execute(
        """
        SELECT COUNT(DISTINCT category) AS total_categories
        FROM processed_events
        WHERE user_id = ?
            AND (status = 'completed' OR answer_id = ?)
            AND category IS NOT NULL;
        """,
        (user_id, answer_id),
    ).fetchone()
    return int(row["total_categories"])


def _count_followers(connection: sqlite3.Connection, user_id: int) -> int:
    row = connection.execute(
        "SELECT followers_count FROM follower_counts WHERE user_id = ?;",
        (user_id,),
    ).fetchone()
    return int(row["followers_count"]) if row is not None else 0


def _award_by_metrics(
    *,
    connection: sqlite3.Connection,
    user_id: int,
    total_answers: int,
    distinct_surveys: int,
    distinct_categories: int,
    followers: int,
) -> list[dict[str, object]]:
    achievements = connection.execute(
        """
        SELECT id, name, description, condition_type, condition_value
        FROM achievements
        ORDER BY id;
        """
    ).fetchall()

    awarded: list[dict[str, object]] = []
    for achievement in achievements:
        if not _condition_met(
            condition_type=str(achievement["condition_type"]),
            condition_value=int(achievement["condition_value"]),
            total_answers=total_answers,
            distinct_surveys=distinct_surveys,
            distinct_categories=distinct_categories,
            followers=followers,
        ):
            continue

        awarded_at = utcnow()
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO user_achievements (user_id, achievement_id, awarded_at)
            VALUES (?, ?, ?);
            """,
            (user_id, int(achievement["id"]), awarded_at),
        )
        if cursor.rowcount:
            awarded.append(
                {
                    "id": int(achievement["id"]),
                    "name": str(achievement["name"]),
                    "description": str(achievement["description"]),
                    "awarded_at": awarded_at,
                }
            )
    return awarded


def _condition_met(
    *,
    condition_type: str,
    condition_value: int,
    total_answers: int,
    distinct_surveys: int,
    distinct_categories: int,
    followers: int,
) -> bool:
    if condition_type == "total_answers":
        return total_answers >= condition_value

    if condition_type == "distinct_surveys":
        return distinct_surveys >= condition_value

    if condition_type == "distinct_categories":
        return distinct_categories >= condition_value

    if condition_type == "followers":
        return followers >= condition_value

    return False
