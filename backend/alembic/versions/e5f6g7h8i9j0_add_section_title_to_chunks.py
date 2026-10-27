"""add section_title to chunks

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-03-08 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "e5f6g7h8i9j0"
down_revision = "d4e5f6g7h8i9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("section_title", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("chunks", "section_title")
