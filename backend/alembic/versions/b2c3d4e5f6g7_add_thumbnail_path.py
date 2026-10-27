"""add thumbnail_path to videos

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-12 21:06:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "b2c3d4e5f6g7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("thumbnail_path", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("videos", "thumbnail_path")
