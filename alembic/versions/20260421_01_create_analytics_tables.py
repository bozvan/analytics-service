from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260421_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "question_stats",
        sa.Column("survey_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column(
            "answer_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.PrimaryKeyConstraint("survey_id", "question_id"),
    )
    op.create_index(
        "ix_question_stats_survey_id",
        "question_stats",
        ["survey_id"],
        unique=False,
    )

    op.create_table(
        "processed_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("answer_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("survey_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name="ck_processed_events_status",
        ),
        sa.UniqueConstraint("answer_id", name="uq_processed_events_answer_id"),
    )
    op.create_index(
        "ix_processed_events_user_status",
        "processed_events",
        ["user_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_processed_events_user_survey_status",
        "processed_events",
        ["user_id", "survey_id", "status"],
        unique=False,
    )

    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("answer_id", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name="ck_idempotency_keys_status",
        ),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index(
        "ix_idempotency_keys_answer_id",
        "idempotency_keys",
        ["answer_id"],
        unique=False,
    )

    op.create_table(
        "achievements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("condition_type", sa.String(length=32), nullable=False),
        sa.Column("condition_value", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_achievements_name"),
    )
    op.create_index(
        "ix_achievements_condition",
        "achievements",
        ["condition_type", "condition_value"],
        unique=False,
    )

    op.create_table(
        "user_achievements",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("achievement_id", sa.Integer(), nullable=False),
        sa.Column("awarded_at", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["achievement_id"],
            ["achievements.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "achievement_id"),
    )
    op.create_index(
        "ix_user_achievements_user_id",
        "user_achievements",
        ["user_id"],
        unique=False,
    )

    achievements = sa.table(
        "achievements",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.Text()),
        sa.column("description", sa.Text()),
        sa.column("condition_type", sa.String(length=32)),
        sa.column("condition_value", sa.Integer()),
    )

    op.bulk_insert(
        achievements,
        [
            {
                "id": 1,
                "name": "Первый ответ",
                "description": "Пользователь отправил свой первый ответ.",
                "condition_type": "total_answers",
                "condition_value": 1,
            },
            {
                "id": 2,
                "name": "10 ответов",
                "description": "Пользователь отправил 10 ответов.",
                "condition_type": "total_answers",
                "condition_value": 10,
            },
            {
                "id": 3,
                "name": "100 ответов",
                "description": "Пользователь отправил 100 ответов.",
                "condition_type": "total_answers",
                "condition_value": 100,
            },
            {
                "id": 4,
                "name": "Мастер опросов",
                "description": "Пользователь ответил как минимум в 5 разных опросах.",
                "condition_type": "distinct_surveys",
                "condition_value": 5,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_user_achievements_user_id", table_name="user_achievements")
    op.drop_table("user_achievements")

    op.drop_index("ix_achievements_condition", table_name="achievements")
    op.drop_table("achievements")

    op.drop_index("ix_idempotency_keys_answer_id", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")

    op.drop_index(
        "ix_processed_events_user_survey_status",
        table_name="processed_events",
    )
    op.drop_index("ix_processed_events_user_status", table_name="processed_events")
    op.drop_table("processed_events")

    op.drop_index("ix_question_stats_survey_id", table_name="question_stats")
    op.drop_table("question_stats")
