"""fase7: no_asistida en EstadoCita y campo bloqueado en Usuario

Revision ID: b3f92a1c8e07
Revises: 4e1e00b485a6
Create Date: 2026-06-14

"""
from alembic import op
import sqlalchemy as sa

revision = "b3f92a1c8e07"
down_revision = "4e1e00b485a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Ampliar la columna citas.estado de VARCHAR(10) a VARCHAR(15)
    #    para que quepa 'no_asistida' (12 caracteres).
    op.alter_column(
        "citas",
        "estado",
        existing_type=sa.String(10),
        type_=sa.String(15),
        existing_nullable=False,
    )

    # 2. Sustituir el CHECK constraint por uno que incluya 'no_asistida'.
    op.drop_constraint("ck_cita_estado", "citas", type_="check")
    op.create_check_constraint(
        "ck_cita_estado",
        "citas",
        "estado IN ('activa','cancelada','no_asistida')",
    )

    # 3. Añadir columna bloqueado a usuarios (default false para filas existentes).
    op.add_column(
        "usuarios",
        sa.Column("bloqueado", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    # 3. Quitar bloqueado
    op.drop_column("usuarios", "bloqueado")

    # 2. Revertir 'no_asistida' a 'activa' para poder restaurar el CHECK estricto
    op.execute("UPDATE citas SET estado='activa' WHERE estado='no_asistida'")
    op.drop_constraint("ck_cita_estado", "citas", type_="check")
    op.create_check_constraint(
        "ck_cita_estado",
        "citas",
        "estado IN ('activa','cancelada')",
    )

    # 1. Reducir columna de vuelta a VARCHAR(10)
    op.alter_column(
        "citas",
        "estado",
        existing_type=sa.String(15),
        type_=sa.String(10),
        existing_nullable=False,
    )
