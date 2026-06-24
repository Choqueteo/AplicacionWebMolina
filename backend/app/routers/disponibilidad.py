from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.constants import DIAS_MAX_RESERVA, FRANJA_MINUTOS
from app.database import get_db
from app.dependencies import get_usuario_actual
from app.models import ExcepcionFecha, FranjaOcupada, HorarioPeluquero, Servicio, TipoExcepcion, Usuario
from app.schemas import DisponibilidadRead

router = APIRouter(tags=["disponibilidad"])

_MADRID = ZoneInfo("Europe/Madrid")


def _calcular_disponibles(
    apertura: datetime,
    cierre: datetime,
    duracion_minutos: int,
    ocupadas: set,
    ahora_madrid: datetime | None,
) -> list:
    """
    Devuelve las horas de inicio disponibles para un servicio de `duracion_minutos`
    dentro del tramo [apertura, cierre].

    `apertura` y `cierre` son datetime.time convertidos a datetime (misma fecha base).
    `ahora_madrid` se usa para filtrar horas pasadas cuando la fecha consultada es hoy.
    """
    N = duracion_minutos // FRANJA_MINUTOS
    disponibles = []

    # Último inicio válido: cierre - duracion_minutos
    ultimo_inicio = cierre - timedelta(minutes=duracion_minutos)

    current = apertura
    while current <= ultimo_inicio:
        franja_inicio = current.time()

        # Filtrar slots pasados cuando la fecha es hoy
        if ahora_madrid is not None and franja_inicio <= ahora_madrid:
            current += timedelta(minutes=FRANJA_MINUTOS)
            continue

        # Comprobar que las N franjas consecutivas están libres
        all_free = all(
            (current + timedelta(minutes=FRANJA_MINUTOS * i)).time() not in ocupadas
            for i in range(N)
        )

        if all_free:
            disponibles.append(franja_inicio)

        current += timedelta(minutes=FRANJA_MINUTOS)

    return disponibles


@router.get("/disponibilidad", response_model=DisponibilidadRead)
def consultar_disponibilidad(
    fecha: date,
    servicio_id: int,
    _: Usuario = Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    servicio = db.get(Servicio, servicio_id)
    if not servicio or not servicio.activo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Servicio no encontrado o inactivo",
        )

    now_madrid = datetime.now(_MADRID)
    today_madrid = now_madrid.date()

    # Fecha fuera de ventana de reserva → sin disponibilidad (no error)
    if fecha < today_madrid or fecha > today_madrid + timedelta(days=DIAS_MAX_RESERVA):
        return DisponibilidadRead(fecha=fecha, servicio_id=servicio_id, horas_disponibles=[])

    # Fecha cerrada → sin disponibilidad (no error)
    if db.query(ExcepcionFecha).filter_by(fecha=fecha, tipo=TipoExcepcion.cerrado).first():
        return DisponibilidadRead(fecha=fecha, servicio_id=servicio_id, horas_disponibles=[])

    # Buscar todos los tramos del día de la semana
    dia_semana = fecha.weekday()
    tramos = (
        db.query(HorarioPeluquero)
        .filter_by(dia_semana=dia_semana)
        .order_by(HorarioPeluquero.hora_apertura)
        .all()
    )
    if not tramos:
        return DisponibilidadRead(fecha=fecha, servicio_id=servicio_id, horas_disponibles=[])

    # Franjas ya ocupadas ese día (una sola consulta)
    ocupadas = {
        row.hora
        for row in db.query(FranjaOcupada).filter(FranjaOcupada.fecha == fecha).all()
    }

    from datetime import date as _date
    ahora_t = now_madrid.time() if fecha == today_madrid else None

    horas = []
    for tramo in tramos:
        base      = datetime.combine(_date.min, tramo.hora_apertura)
        cierre_dt = datetime.combine(_date.min, tramo.hora_cierre)
        horas.extend(_calcular_disponibles(
            apertura=base,
            cierre=cierre_dt,
            duracion_minutos=servicio.duracion_minutos,
            ocupadas=ocupadas,
            ahora_madrid=ahora_t,
        ))

    return DisponibilidadRead(fecha=fecha, servicio_id=servicio_id, horas_disponibles=horas)
