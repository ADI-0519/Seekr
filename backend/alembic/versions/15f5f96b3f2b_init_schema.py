"""init schema

Revision ID: 15f5f96b3f2b
Revises:
Create Date: 2026-02-04 19:45:09.042912

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "15f5f96b3f2b"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("youtube_url", sa.String(500), nullable=True),
        sa.Column("storage_path", sa.String(500), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("current_stage", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "sentences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_sentences_video_time",
        "sentences",
        ["video_id", "start_time", "end_time"],
    )

    op.create_table(
        "segments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_segments_video_time",
        "segments",
        ["video_id", "start_time", "end_time"],
    )

    op.create_table(
        "slide_frames",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("frame_path", sa.String(500), nullable=True),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_slide_frames_video_time",
        "slide_frames",
        ["video_id", "start_time", "end_time"],
    )


def downgrade() -> None:
    op.drop_index("ix_slide_frames_video_time", table_name="slide_frames")
    op.drop_table("slide_frames")
    op.drop_index("ix_segments_video_time", table_name="segments")
    op.drop_table("segments")
    op.drop_index("ix_sentences_video_time", table_name="sentences")
    op.drop_table("sentences")
    op.drop_table("processing_jobs")
    op.drop_table("videos")
