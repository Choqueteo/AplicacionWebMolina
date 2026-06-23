"""franja_30_duracion_max

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-06-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "b2c3d4e5f6a1"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_servicio_duracion", "servicios", type_="check")
    op.create_check_constraint(
        "ck_servicio_duracion",
        "servicios",
        "duracion_minutos > 0 AND duracion_minutos <= 300 AND mod(duracion_minutos, 30) = 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_servicio_duracion", "servicios", type_="check")
    op.create_check_constraint(
        "ck_servicio_duracion",
        "servicios",
        "duracion_minutos > 0 AND mod(duracion_minutos, 15) = 0",
    )
