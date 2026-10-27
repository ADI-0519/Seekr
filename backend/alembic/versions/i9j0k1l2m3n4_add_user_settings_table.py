"""add user_settings table

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-03-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "i9j0k1l2m3n4"
down_revision: Union[str, Sequence[str], None] = "h8i9j0k1l2m3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_settings",
        sa.Column("uid", sa.String(length=128), nullable=False),
        sa.Column("theme_mode", sa.String(length=16), nullable=False, server_default="light"),
        sa.Column(
            "background_mode", sa.String(length=16), nullable=False, server_default="animated"
        ),
        sa.Column("autoplay_next", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("volume_default", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("muted_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("preferred_language", sa.String(length=16), nullable=False, server_default="en"),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("uid"),
    )


def downgrade() -> None:
    op.drop_table("user_settings")
