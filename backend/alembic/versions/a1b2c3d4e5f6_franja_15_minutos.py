"""franja_15_minutos

Revision ID: a1b2c3d4e5f6
Revises: c70da527d6e9
Create Date: 2026-06-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "c70da527d6e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_servicio_duracion", "servicios", type_="check")
    op.create_check_constraint(
        "ck_servicio_duracion",
        "servicios",
        "duracion_minutos > 0 AND mod(duracion_minutos, 15) = 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_servicio_duracion", "servicios", type_="check")
    op.create_check_constraint(
        "ck_servicio_duracion",
        "servicios",
        "duracion_minutos > 0 AND mod(duracion_minutos, 30) = 0",
    )
