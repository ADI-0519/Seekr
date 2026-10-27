"""add audio_path to videos

Revision ID: a1b2c3d4e5f6
Revises: 15f5f96b3f2b
Create Date: 2026-02-12 15:18:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "15f5f96b3f2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("audio_path", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("videos", "audio_path")
