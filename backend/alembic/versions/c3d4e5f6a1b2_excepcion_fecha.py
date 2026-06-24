"""excepcion_fecha

Revision ID: c3d4e5f6a1b2
Revises: b2c3d4e5f6a1
Create Date: 2026-06-24 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a1b2"
down_revision: Union[str, None] = "b2c3d4e5f6a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "excepcion_fecha",
        sa.Column("id",    sa.Integer,    primary_key=True),
        sa.Column("fecha", sa.Date,       nullable=False),
        sa.Column("tipo",  sa.String(20), nullable=False, server_default="cerrado"),
        sa.UniqueConstraint("fecha", name="uq_excepcion_fecha"),
    )


def downgrade() -> None:
    op.drop_table("excepcion_fecha")
