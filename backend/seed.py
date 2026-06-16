"""
Crea o actualiza las cuentas de administrador en la base de datos.
Idempotente: si el admin ya existe actualiza su contraseña, nombre y teléfono;
nunca crea duplicados ni más de los 2 admins configurados.

Uso:
    cd backend
    venv\\Scripts\\python seed.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal  # noqa: E402
from app.models import Rol, Usuario    # noqa: E402
from app.security import hash_password  # noqa: E402

_ADMINS = [
    ("ADMIN1_EMAIL", "ADMIN1_PASSWORD", "ADMIN1_NOMBRE", "ADMIN1_TELEFONO"),
    ("ADMIN2_EMAIL", "ADMIN2_PASSWORD", "ADMIN2_NOMBRE", "ADMIN2_TELEFONO"),
]


def seed() -> None:
    db = SessionLocal()
    try:
        for email_var, pwd_var, nombre_var, tel_var in _ADMINS:
            email    = os.environ[email_var]
            password = os.environ[pwd_var]
            nombre   = os.environ.get(nombre_var, "Admin")
            telefono = os.environ.get(tel_var, "000000000")

            existente = db.query(Usuario).filter_by(email=email).first()
            if existente:
                existente.password_hash  = hash_password(password)
                existente.nombre_completo = nombre
                existente.telefono        = telefono
                existente.rol             = Rol.admin
                print(f"[seed] {email} actualizado.")
            else:
                db.add(Usuario(
                    email=email,
                    password_hash=hash_password(password),
                    telefono=telefono,
                    nombre_completo=nombre,
                    rol=Rol.admin,
                ))
                print(f"[seed] {email} creado como admin.")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
