from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.constants import DIAS_MAX_RESERVA
from app.database import get_db
from app.dependencies import get_usuario_actual, solo_admin
from app.models import Cita, EstadoCita, ExcepcionFecha, TipoExcepcion, Usuario
from app.schemas import ExcepcionFechaCreate, ExcepcionFechaRead

router = APIRouter(tags=["excepciones"])
_MADRID = ZoneInfo("Europe/Madrid")


# Literales antes que rutas con parámetro (CLAUDE.md)

@router.get("/excepciones", response_model=list[ExcepcionFechaRead])
def listar_excepciones(_: Usuario = Depends(solo_admin), db: Session = Depends(get_db)):
    return db.query(ExcepcionFecha).order_by(ExcepcionFecha.fecha).all()


@router.get("/excepciones/proximas", response_model=list[ExcepcionFechaRead])
def listar_excepciones_proximas(
    _: Usuario = Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    today_madrid = datetime.now(_MADRID).date()
    limite = today_madrid + timedelta(days=DIAS_MAX_RESERVA)
    return (
        db.query(ExcepcionFecha)
        .filter(
            ExcepcionFecha.fecha >= today_madrid,
            ExcepcionFecha.fecha <= limite,
            ExcepcionFecha.tipo == TipoExcepcion.cerrado,
        )
        .order_by(ExcepcionFecha.fecha)
        .all()
    )


@router.post("/excepciones", response_model=ExcepcionFechaRead, status_code=status.HTTP_201_CREATED)
def crear_excepcion(
    datos: ExcepcionFechaCreate,
    _: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    if db.query(ExcepcionFecha).filter_by(fecha=datos.fecha).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esa fecha ya está cerrada")

    n_citas = db.query(Cita).filter(
        Cita.fecha == datos.fecha, Cita.estado == EstadoCita.activa
    ).count()
    if n_citas:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede cerrar: hay {n_citas} cita(s) activa(s) ese día",
        )

    exc = ExcepcionFecha(fecha=datos.fecha, tipo=TipoExcepcion.cerrado)
    db.add(exc)
    db.commit()
    db.refresh(exc)
    return exc


@router.delete("/excepciones/{excepcion_id}", response_model=ExcepcionFechaRead)
def eliminar_excepcion(
    excepcion_id: int,
    _: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    exc = db.get(ExcepcionFecha, excepcion_id)
    if exc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Excepción no encontrada")
    db.delete(exc)
    db.commit()
    return exc
