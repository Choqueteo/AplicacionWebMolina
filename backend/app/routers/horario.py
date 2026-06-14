from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
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


# Ruta literal antes que ruta con parámetro (CLAUDE.md)

@router.get("/horario", response_model=list[HorarioRead])
def listar_horario(
    _: Usuario = Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    return db.query(HorarioPeluquero).order_by(HorarioPeluquero.dia_semana).all()


@router.post("/horario", response_model=HorarioRead, status_code=status.HTTP_201_CREATED)
def crear_horario(
    datos: HorarioCreate,
    _: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    tramo = HorarioPeluquero(**datos.model_dump())
    db.add(tramo)
    try:
        db.commit()
        db.refresh(tramo)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un tramo para ese día de la semana",
        )
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
    # Revalidar que apertura < cierre con los valores combinados
    if tramo.hora_cierre <= tramo.hora_apertura:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="hora_cierre debe ser posterior a hora_apertura",
        )
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
