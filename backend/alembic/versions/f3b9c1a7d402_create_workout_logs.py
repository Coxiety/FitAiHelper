"""create workout logs

Revision ID: f3b9c1a7d402
Revises: a8d0fa0cf86f
Create Date: 2026-11-16 12:46:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f3b9c1a7d402'
down_revision: Union[str, None] = 'a8d0fa0cf86f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

workout_category = postgresql.ENUM(
    "cardio", "strength", "mobility", "sport", "other", name="workout_log_category", create_type=False
)
workout_intensity = postgresql.ENUM(
    "light", "moderate", "vigorous", name="workout_log_intensity", create_type=False
)


def upgrade() -> None:
    workout_category.create(op.get_bind(), checkfirst=True)
    workout_intensity.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "workout_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("trained_on", sa.Date(), nullable=False, comment="Ngày tập theo giờ Việt Nam"),
        sa.Column("activity_name", sa.String(length=120), nullable=False),
        sa.Column("category", workout_category, server_default="other", nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False),
        sa.Column("intensity", workout_intensity, server_default="moderate", nullable=False),
        sa.Column("notes", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"),
                  nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("duration_min >= 1 AND duration_min <= 600", name="ck_workout_logs_duration"),
    )
    op.create_index(op.f("ix_workout_logs_user_id"), "workout_logs", ["user_id"], unique=False)
    op.create_index("ix_workout_logs_user_trained_on", "workout_logs", ["user_id", "trained_on"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workout_logs_user_trained_on", table_name="workout_logs")
    op.drop_index(op.f("ix_workout_logs_user_id"), table_name="workout_logs")
    op.drop_table("workout_logs")
    workout_intensity.drop(op.get_bind(), checkfirst=True)
    workout_category.drop(op.get_bind(), checkfirst=True)
