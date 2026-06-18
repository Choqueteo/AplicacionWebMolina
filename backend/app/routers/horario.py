from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_usuario_actual, solo_admin
from app.models import HorarioPeluquero, Usuario
from app.schemas import HorarioCreate, HorarioRead, HorarioUpdate

router = APIRouter(tags=["horario"])


def _get_or_404(horario_id: int, db: Session) -> HorarioPeluquero:
    tramo = db.get(HorarioPeluquero, horario_id)
    if not tramo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tramo de horario no encontrado")
    return tramo


def _validar_sin_solapamiento(db: Session, dia_semana: int, apertura, cierre, excluir_id: int | None = None) -> None:
    q = db.query(HorarioPeluquero).filter(HorarioPeluquero.dia_semana == dia_semana)
    if excluir_id is not None:
        q = q.filter(HorarioPeluquero.id != excluir_id)
    for t in q.all():
        if not (cierre <= t.hora_apertura or apertura >= t.hora_cierre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El tramo se solapa con uno existente ese día",
            )


# Ruta literal antes que ruta con parámetro (CLAUDE.md)

@router.get("/horario", response_model=list[HorarioRead])
def listar_horario(
    _: Usuario = Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    return db.query(HorarioPeluquero).order_by(HorarioPeluquero.dia_semana, HorarioPeluquero.hora_apertura).all()


@router.post("/horario", response_model=HorarioRead, status_code=status.HTTP_201_CREATED)
def crear_horario(
    datos: HorarioCreate,
    _: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    _validar_sin_solapamiento(db, datos.dia_semana, datos.hora_apertura, datos.hora_cierre)
    tramo = HorarioPeluquero(**datos.model_dump())
    db.add(tramo)
    db.commit()
    db.refresh(tramo)
    return tramo


@router.put("/horario/{horario_id}", response_model=HorarioRead)
def actualizar_horario(
    horario_id: int,
    datos: HorarioUpdate,
    _: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    tramo = _get_or_404(horario_id, db)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(tramo, campo, valor)
    if tramo.hora_cierre <= tramo.hora_apertura:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="hora_cierre debe ser posterior a hora_apertura",
        )
    _validar_sin_solapamiento(db, tramo.dia_semana, tramo.hora_apertura, tramo.hora_cierre, excluir_id=tramo.id)
    db.commit()
    db.refresh(tramo)
    return tramo


@router.delete("/horario/{horario_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_horario(
    horario_id: int,
    _: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    tramo = _get_or_404(horario_id, db)
    db.delete(tramo)
    db.commit()
