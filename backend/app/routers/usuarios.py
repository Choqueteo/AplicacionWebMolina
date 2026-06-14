from sqlalchemy import func
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.dependencies import solo_admin
from app.models import Cita, EstadoCita, Rol, Usuario
from app.schemas import UsuarioAdminRead

router = APIRouter(tags=["usuarios"])


def _inasistencias(db: Session, usuario_id: int) -> int:
    return (
        db.query(Cita)
        .filter(Cita.cliente_id == usuario_id, Cita.estado == EstadoCita.no_asistida)
        .count()
    )


def _to_read(usuario: Usuario, count: int) -> UsuarioAdminRead:
    return UsuarioAdminRead(
        id=usuario.id,
        email=usuario.email,
        telefono=usuario.telefono,
        nombre_completo=usuario.nombre_completo,
        rol=usuario.rol,
        bloqueado=usuario.bloqueado,
        inasistencias=count,
    )


# ---------------------------------------------------------------------------
# Rutas — literales antes que rutas con parámetro (CLAUDE.md)
# ---------------------------------------------------------------------------

@router.get("/usuarios", response_model=list[UsuarioAdminRead])
def listar_usuarios(
    _: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """Lista todos los usuarios con su contador de inasistencias. Solo admin."""
    usuarios = db.query(Usuario).order_by(Usuario.id).all()

    # Una sola consulta GROUP BY para evitar N+1
    counts: dict[int, int] = dict(
        db.query(Cita.cliente_id, func.count(Cita.id))
        .filter(Cita.estado == EstadoCita.no_asistida)
        .group_by(Cita.cliente_id)
        .all()
    )
    return [_to_read(u, counts.get(u.id, 0)) for u in usuarios]


@router.get("/usuarios/{usuario_id}", response_model=UsuarioAdminRead)
def obtener_usuario(
    usuario_id: int,
    _: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """Detalle de un usuario con contador de inasistencias. Solo admin."""
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return _to_read(usuario, _inasistencias(db, usuario_id))


@router.patch("/usuarios/{usuario_id}/bloquear", response_model=UsuarioAdminRead)
def bloquear_usuario(
    usuario_id: int,
    _: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """Bloquea a un cliente para que no pueda reservar citas. Solo admin."""
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if usuario.rol == Rol.admin:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se puede bloquear a un administrador",
        )
    usuario.bloqueado = True
    db.commit()
    db.refresh(usuario)
    return _to_read(usuario, _inasistencias(db, usuario_id))


@router.patch("/usuarios/{usuario_id}/desbloquear", response_model=UsuarioAdminRead)
def desbloquear_usuario(
    usuario_id: int,
    _: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """Desbloquea a un cliente para que pueda volver a reservar citas. Solo admin."""
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if usuario.rol == Rol.admin:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se puede desbloquear a un administrador",
        )
    usuario.bloqueado = False
    db.commit()
    db.refresh(usuario)
    return _to_read(usuario, _inasistencias(db, usuario_id))
