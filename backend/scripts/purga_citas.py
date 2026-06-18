"""
Purga citas (y sus franjas) anteriores a la ventana de retención.

Uso:
    cd backend
    python scripts/purga_citas.py [--dry-run]

El script es idempotente: ejecutarlo varias veces tiene el mismo efecto que ejecutarlo una.
La variable de entorno RETENCION_MESES (por defecto 24) controla la ventana.
"""
import argparse
import os
import sys
from datetime import date

# Permite importar 'app.*' cuando el script se ejecuta directamente desde backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Cita, FranjaOcupada


def _fecha_limite(retencion_meses: int | None = None) -> date:
    """Devuelve la fecha límite: hoy menos la ventana de retención."""
    meses = retencion_meses if retencion_meses is not None else settings.retencion_meses
    hoy = date.today()
    anio = hoy.year - meses // 12
    mes  = hoy.month - meses % 12
    if mes <= 0:
        mes  += 12
        anio -= 1
    return hoy.replace(year=anio, month=mes)


def purgar(dry_run: bool = False, db: Session | None = None, _limite: date | None = None) -> int:
    """
    Borra citas cuya fecha sea anterior a la ventana de retención junto con sus FranjaOcupada.

    Args:
        dry_run: Si True, solo cuenta y muestra sin borrar nada.
        db:      Sesión SQLAlchemy externa (usada en tests). Si None, crea una propia.
        _limite: Fecha límite explícita (usada en tests). Si None, usa _fecha_limite().

    Returns:
        Número de citas que se habrían borrado (dry_run=True) o que se borraron (dry_run=False).
    """
    limite = _limite if _limite is not None else _fecha_limite()

    _own_session = db is None
    if _own_session:
        db = SessionLocal()
    try:
        ids = [r[0] for r in db.query(Cita.id).filter(Cita.fecha < limite).all()]

        if not ids:
            print("Nada que purgar.")
            return 0

        if dry_run:
            print(f"[dry-run] Se borrarían {len(ids)} citas anteriores a {limite}.")
            return len(ids)

        db.execute(delete(FranjaOcupada).where(FranjaOcupada.cita_id.in_(ids)))
        db.execute(delete(Cita).where(Cita.id.in_(ids)))
        db.commit()
        print(f"Purgadas {len(ids)} citas anteriores a {limite}.")
        return len(ids)
    finally:
        if _own_session:
            db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Purga citas antiguas de la BD.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo cuenta cuántas citas se borrarían, sin borrar nada.",
    )
    args = parser.parse_args()
    purgar(dry_run=args.dry_run)
