"""add transcript_words table

Revision ID: c3d4e5f6g7h8
Revises: 8b7f643ff6da
Create Date: 2026-02-26 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "c3d4e5f6g7h8"
down_revision = "8b7f643ff6da"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transcript_words",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("word", sa.String(100), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("probability", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_transcript_words_video_time",
        "transcript_words",
        ["video_id", "start_time"],
    )


def downgrade() -> None:
    op.drop_index("ix_transcript_words_video_time", table_name="transcript_words")
    op.drop_table("transcript_words")
