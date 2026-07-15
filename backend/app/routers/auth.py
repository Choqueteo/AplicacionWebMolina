from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_usuario_actual
from app.models import Cita, EstadoCita, FranjaOcupada, Rol, Servicio, Usuario
from app.rate_limit import limiter
from app.schemas import (
    ActualizarPerfilIn,
    CambiarPasswordIn,
    CitaExport,
    LoginRequest,
    PerfilExport,
    Token,
    UsuarioCreate,
    UsuarioDatosExport,
    UsuarioRead,
)
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(tags=["autenticación"])

CONSENTIMIENTO_VERSION = "v1"
HASH_ANONIMIZADO = "ANONIMIZADO"

_DUMMY_HASH = hash_password("__dummy_password_never_used__")


def _cancelar_citas_futuras(
    db: Session, usuario: Usuario, today_madrid: date, now_madrid: datetime
) -> None:
    """Cancela citas activas futuras del usuario y libera sus franjas. Sin commit."""
    citas_activas = db.query(Cita).filter(
        Cita.cliente_id == usuario.id,
        Cita.estado == EstadoCita.activa,
    ).all()
    for cita in citas_activas:
        es_pasada = (cita.fecha < today_madrid) or (
            cita.fecha == today_madrid and cita.hora_inicio <= now_madrid.time()
        )
        if not es_pasada:
            cita.estado = EstadoCita.cancelada
            db.query(FranjaOcupada).filter(
                FranjaOcupada.cita_id == cita.id
            ).delete(synchronize_session="fetch")


@router.post("/registro", response_model=UsuarioRead, status_code=201)
@limiter.limit("5/minute")
def registro(request: Request, datos: UsuarioCreate, db: Session = Depends(get_db)):
    usuario = Usuario(
        email=datos.email,
        password_hash=hash_password(datos.password),
        telefono=datos.telefono,
        nombre_completo=datos.nombre_completo,
        rol=Rol.cliente,  # FORZADO: nunca se lee del cuerpo de la petición
        consentimiento_version=CONSENTIMIENTO_VERSION,
        consentimiento_fecha=datetime.now(ZoneInfo("Europe/Madrid")),
    )
    db.add(usuario)
    try:
        db.commit()
        db.refresh(usuario)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="El email ya está registrado")
    return usuario


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, datos: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()

    # Ejecutar bcrypt siempre para no filtrar existencia de email por timing
    hash_a_verificar = usuario.password_hash if usuario else _DUMMY_HASH
    contrasena_valida = verify_password(datos.password, hash_a_verificar)

    if not usuario or not contrasena_valida:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    return Token(access_token=create_access_token(usuario.id, usuario.rol.value))


@router.get("/usuarios/me/datos", response_model=UsuarioDatosExport)
def exportar_mis_datos(
    usuario: Usuario = Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    servicio_ids = {cita.servicio_id for cita in usuario.citas}
    servicios = (
        {s.id: s for s in db.query(Servicio).filter(Servicio.id.in_(servicio_ids)).all()}
        if servicio_ids else {}
    )

    citas_export = [
        CitaExport(
            id=cita.id,
            fecha=cita.fecha,
            hora_inicio=cita.hora_inicio,
            hora_fin=cita.hora_fin,
            estado=cita.estado.value,
            servicio_nombre=(
                servicios[cita.servicio_id].nombre
                if cita.servicio_id in servicios else "Servicio eliminado"
            ),
            servicio_duracion_minutos=(
                servicios[cita.servicio_id].duracion_minutos
                if cita.servicio_id in servicios else 0
            ),
        )
        for cita in usuario.citas
    ]
    perfil = PerfilExport(
        id=usuario.id,
        email=usuario.email,
        nombre_completo=usuario.nombre_completo,
        telefono=usuario.telefono,
        rol=usuario.rol.value,
        consentimiento_version=usuario.consentimiento_version,
        consentimiento_fecha=usuario.consentimiento_fecha,
    )
    return UsuarioDatosExport(perfil=perfil, citas=citas_export)


@router.get("/usuarios/me", response_model=UsuarioRead)
def me(usuario: Usuario = Depends(get_usuario_actual)):
    return usuario


@router.patch("/usuarios/me", response_model=UsuarioRead)
def actualizar_perfil(
    datos: ActualizarPerfilIn,
    usuario: Usuario = Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    if datos.nombre_completo is not None:
        usuario.nombre_completo = datos.nombre_completo
    if datos.telefono is not None:
        usuario.telefono = datos.telefono
    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/usuarios/me/password", status_code=200)
@limiter.limit("5/minute")
def cambiar_password(
    request: Request,
    datos: CambiarPasswordIn,
    usuario: Usuario = Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    if not verify_password(datos.password_actual, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual no es correcta",
        )
    usuario.password_hash = hash_password(datos.password_nueva)
    db.commit()
    return {"detail": "Contraseña actualizada correctamente"}


@router.delete("/usuarios/me", status_code=200)
@limiter.limit("3/minute")
def eliminar_mi_cuenta(
    request: Request,
    usuario: Usuario = Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    if usuario.rol == Rol.admin:
        raise HTTPException(status_code=403, detail="Las cuentas admin no pueden autoeliminarse")

    now_madrid   = datetime.now(ZoneInfo("Europe/Madrid"))
    today_madrid = now_madrid.date()

    _cancelar_citas_futuras(db, usuario, today_madrid, now_madrid)

    usuario.email           = f"anon_{usuario.id}@rmolinastyle.invalid"
    usuario.nombre_completo = "Usuario eliminado"
    usuario.telefono        = "000000000"
    usuario.password_hash   = HASH_ANONIMIZADO

    db.commit()
    return {"detail": "Tu cuenta ha sido anonimizada y tus datos personales eliminados."}
