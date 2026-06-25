"""
Recordatorio diario de citas al peluquero por Telegram.
Render Cron: schedule "0 20 * * *" (20:00 UTC = 22:00 Madrid CEST).
"Mañana" se calcula SIEMPRE en Europe/Madrid, no depende de la hora UTC del cron.

Uso local:
    cd backend && python scripts/recordatorio_diario.py
"""
import os
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import Cita, EstadoCita
from app.notificaciones.telegram import enviar_aviso_peluquero

_MADRID = ZoneInfo("Europe/Madrid")


def enviar_recordatorio(db: Session | None = None, _manana: date | None = None) -> str:
    """
    Construye y envía al peluquero el resumen de citas del día siguiente.

    Args:
        db:      Sesión SQLAlchemy externa (para tests). Si None, crea la propia.
        _manana: Fecha "mañana" explícita (para tests). Si None, calcula en Europe/Madrid.

    Returns:
        El mensaje enviado (útil para assertions en tests).
    """
    manana = _manana if _manana is not None else datetime.now(_MADRID).date() + timedelta(days=1)

    _own_session = db is None
    if _own_session:
        db = SessionLocal()
    try:
        citas = (
            db.query(Cita)
            .filter(Cita.estado == EstadoCita.activa, Cita.fecha == manana)
            .options(joinedload(Cita.cliente))
            .order_by(Cita.hora_inicio)
            .all()
        )

        fecha_str = manana.strftime("%d/%m")
        if not citas:
            mensaje = f"Mañana {fecha_str} no tienes citas."
        else:
            lineas = [f"Citas para mañana {fecha_str}:"]
            for cita in citas:
                hora   = cita.hora_inicio.strftime("%H:%M")
                nombre = cita.cliente.nombre_completo
                lineas.append(f"{hora} — {nombre}")
            mensaje = "\n".join(lineas)

        enviar_aviso_peluquero(mensaje)
        return mensaje
    finally:
        if _own_session:
            db.close()


if __name__ == "__main__":
    enviar_recordatorio()
