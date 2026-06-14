import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Rol, Usuario
from app.security import decode_access_token

# auto_error=False: devuelve None en vez de 403 cuando falta el header,
# permitiendo que get_usuario_actual emita 401 en todos los casos de fallo.
bearer_scheme = HTTPBearer(auto_error=False)


def get_usuario_actual(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o caducado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    usuario = db.get(Usuario, int(payload["sub"]))
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario


def solo_admin(usuario: Usuario = Depends(get_usuario_actual)) -> Usuario:
    if usuario.rol != Rol.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso reservado a administradores",
        )
    return usuario
