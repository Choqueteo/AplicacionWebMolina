from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_usuario_actual, solo_admin
from app.models import Rol, Servicio, Usuario
from app.schemas import ServicioCreate, ServicioRead, ServicioUpdate

router = APIRouter(tags=["servicios"])


def _get_or_404(servicio_id: int, db: Session) -> Servicio:
    servicio = db.get(Servicio, servicio_id)
    if not servicio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Servicio no encontrado")
    return servicio


# Ruta literal antes que ruta con parámetro (CLAUDE.md)

@router.get("/servicios", response_model=list[ServicioRead])
def listar_servicios(
    incluir_inactivos: bool = False,
    usuario: Usuario = Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    query = db.query(Servicio)
    # Los clientes nunca ven inactivos aunque lo pidan explícitamente
    if not incluir_inactivos or usuario.rol != Rol.admin:
        query = query.filter(Servicio.activo == True)  # noqa: E712
    return query.all()


@router.post("/servicios", response_model=ServicioRead, status_code=status.HTTP_201_CREATED)
def crear_servicio(
    datos: ServicioCreate,
    _: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    servicio = Servicio(**datos.model_dump())
    db.add(servicio)
    db.commit()
    db.refresh(servicio)
    return servicio


@router.get("/servicios/{servicio_id}", response_model=ServicioRead)
def obtener_servicio(
    servicio_id: int,
    usuario: Usuario = Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    servicio = _get_or_404(servicio_id, db)
    # Los clientes no pueden acceder a servicios inactivos
    if not servicio.activo and usuario.rol != Rol.admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Servicio no encontrado")
    return servicio


@router.put("/servicios/{servicio_id}", response_model=ServicioRead)
def actualizar_servicio(
    servicio_id: int,
    datos: ServicioUpdate,
    _: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    servicio = _get_or_404(servicio_id, db)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(servicio, campo, valor)
    db.commit()
    db.refresh(servicio)
    return servicio


@router.delete("/servicios/{servicio_id}", response_model=ServicioRead)
def borrar_servicio(
    servicio_id: int,
    _: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    servicio = _get_or_404(servicio_id, db)
    servicio.activo = False
    db.commit()
    db.refresh(servicio)
    return servicio
