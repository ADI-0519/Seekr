"""add_chunks_table

Revision ID: 8b7f643ff6da
Revises: 15f5f96b3f2b
Create Date: 2026-02-23 17:53:46.122222

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b7f643ff6da"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("slide_text", sa.Text(), nullable=True),
        sa.Column("position_category", sa.String(20), nullable=True),
        sa.Column("context_template", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_chunks_video_time",
        "chunks",
        ["video_id", "start_time", "end_time"],
    )


def downgrade() -> None:
    op.drop_index("ix_chunks_video_time", table_name="chunks")
    op.drop_table("chunks")
