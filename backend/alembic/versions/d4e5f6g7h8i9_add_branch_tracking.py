"""
add branch tracking to processing_jobs

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-03-03 14:50:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "d4e5f6g7h8i9"
down_revision = "c3d4e5f6g7h8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("processing_jobs", sa.Column("transcription_stage", sa.String(50), nullable=True))
    op.add_column("processing_jobs", sa.Column("slides_stage", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("processing_jobs", "slides_stage")
    op.drop_column("processing_jobs", "transcription_stage")
