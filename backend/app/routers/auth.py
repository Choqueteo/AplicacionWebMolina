from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_usuario_actual
from app.models import Rol, Usuario
from app.rate_limit import limiter
from app.schemas import (
    ActualizarPerfilIn,
    CambiarPasswordIn,
    LoginRequest,
    Token,
    UsuarioCreate,
    UsuarioRead,
)
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(tags=["autenticación"])

# Hash bcrypt de un texto fijo, calculado una sola vez al importar el módulo.
# Se usa en /login para ejecutar verify_password incluso cuando el email no existe,
# evitando que diferencias de tiempo revelen si una dirección está registrada.
_DUMMY_HASH = hash_password("__dummy_password_never_used__")


@router.post("/registro", response_model=UsuarioRead, status_code=201)
@limiter.limit("5/minute")
def registro(request: Request, datos: UsuarioCreate, db: Session = Depends(get_db)):
    usuario = Usuario(
        email=datos.email,
        password_hash=hash_password(datos.password),
        telefono=datos.telefono,
        nombre_completo=datos.nombre_completo,
        rol=Rol.cliente,  # FORZADO: nunca se lee del cuerpo de la petición
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
