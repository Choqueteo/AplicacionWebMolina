"""consentimiento_usuario

Revision ID: d4e5f6a1b2c3
Revises: c3d4e5f6a1b2
Create Date: 2026-07-16

"""
from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a1b2c3"
down_revision = "c3d4e5f6a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("consentimiento_version", sa.String(20), nullable=True))
    op.add_column("usuarios", sa.Column("consentimiento_fecha",   sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("usuarios", "consentimiento_fecha")
    op.drop_column("usuarios", "consentimiento_version")
