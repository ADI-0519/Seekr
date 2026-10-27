"""add owner_uid to videos

Revision ID: g7h8i9j0k1l3
Revises: g7h8i9j0k1l2
Create Date: 2026-03-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g7h8i9j0k1l3"
down_revision: Union[str, Sequence[str], None] = "g7h8i9j0k1l2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("owner_uid", sa.String(length=128), nullable=True))
    op.create_index(op.f("ix_videos_owner_uid"), "videos", ["owner_uid"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_videos_owner_uid"), table_name="videos")
    op.drop_column("videos", "owner_uid")
