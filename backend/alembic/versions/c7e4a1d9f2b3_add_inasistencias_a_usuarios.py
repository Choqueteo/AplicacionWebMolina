"""add inasistencias a usuarios

Revision ID: c7e4a1d9f2b3
Revises: b3f92a1c8e07
Create Date: 2026-06-17

"""
from alembic import op
import sqlalchemy as sa

revision = "c7e4a1d9f2b3"
down_revision = "b3f92a1c8e07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("inasistencias", sa.Integer(), nullable=False, server_default="0"),
    )
    # Backfill: rellena el contador con el histórico existente de citas no_asistida.
    # Después de esto el valor es la fuente de verdad; las citas antiguas se pueden purgar.
    op.execute("""
        UPDATE usuarios
        SET inasistencias = (
            SELECT COUNT(*) FROM citas
            WHERE citas.cliente_id = usuarios.id AND citas.estado = 'no_asistida'
        )
    """)


def downgrade() -> None:
    op.drop_column("usuarios", "inasistencias")
