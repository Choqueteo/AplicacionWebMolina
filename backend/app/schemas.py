import re
from datetime import date, time
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models import EstadoCita

# Letras latinas con tildes/acentos, ñ y caracteres europeos comunes, más espacio, guión y apóstrofo
_NOMBRE_RE = re.compile(
    r"^[a-zA-ZáéíóúàèìòùäëïöüÿâêîôûãõñçÁÉÍÓÚÀÈÌÒÙÄËÏÖÜÂÊÎÔÛÃÕÑÇ '\-]+$"
)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    telefono: str  # validado y normalizado por validar_telefono
    nombre_completo: str = Field(min_length=1, max_length=100)
    # Sin campo `rol`: el endpoint lo fuerza siempre a 'cliente'

    model_config = {"extra": "forbid"}  # 422 ante cualquier campo extra (anti mass-assignment)

    @field_validator("nombre_completo", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        # Normalizar: recortar y colapsar espacios múltiples
        v = " ".join(str(v).split())
        if not v:
            raise ValueError("El nombre completo no puede estar vacío")
        if not _NOMBRE_RE.match(v):
            raise ValueError(
                "El nombre solo puede contener letras, espacios, guiones y apóstrofos"
            )
        palabras = v.split()
        if len(palabras) < 2:
            raise ValueError("Introduce al menos nombre y apellido (mínimo dos palabras)")
        for palabra in palabras:
            letras = sum(1 for c in palabra if c.isalpha())  # isalpha() cubre Unicode
            if letras < 2:
                raise ValueError("Cada parte del nombre debe tener al menos 2 letras")
        return v  # versión normalizada

    @field_validator("telefono", mode="before")
    @classmethod
    def validar_telefono(cls, v: str) -> str:
        # Normalizar: eliminar separadores habituales (espacios, guiones, puntos, paréntesis)
        cleaned = re.sub(r"[\s\-\.\(\)]", "", str(v))
        # Prefijo España (+34 / 0034) opcional; 9 dígitos comenzando por 6/7/8/9
        # Formato canónico guardado: 9 dígitos sin prefijo (ej. "612345678")
        m = re.match(r"^(?:\+34|0034)?([6-9]\d{8})$", cleaned)
        if not m:
            raise ValueError(
                "Teléfono inválido. Introduce un número español de 9 dígitos "
                "(p. ej. 612345678 o +34 612 345 678)"
            )
        return m.group(1)  # canónico: 9 dígitos sin prefijo


class UsuarioRead(BaseModel):
    id: int
    email: str
    telefono: str
    nombre_completo: str
    rol: str

    model_config = {"from_attributes": True}


class UsuarioAdminRead(BaseModel):
    id: int
    email: str
    telefono: str
    nombre_completo: str
    rol: str
    bloqueado: bool
    inasistencias: int  # calculado dinámicamente; no existe como columna en Usuario


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Servicios
# ---------------------------------------------------------------------------

class ServicioCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    duracion_minutos: int = Field(gt=0)
    precio: Decimal = Field(ge=0)

    model_config = {"extra": "forbid"}

    @field_validator("duracion_minutos")
    @classmethod
    def multiplo_de_30(cls, v: int) -> int:
        if v % 30 != 0:
            raise ValueError("duracion_minutos debe ser múltiplo de 30")
        return v


class ServicioUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    duracion_minutos: int | None = Field(default=None, gt=0)
    precio: Decimal | None = Field(default=None, ge=0)

    model_config = {"extra": "forbid"}

    @field_validator("duracion_minutos")
    @classmethod
    def multiplo_de_30(cls, v: int | None) -> int | None:
        if v is not None and v % 30 != 0:
            raise ValueError("duracion_minutos debe ser múltiplo de 30")
        return v


class ServicioRead(BaseModel):
    id: int
    nombre: str
    duracion_minutos: int
    precio: Decimal
    activo: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Horario
# ---------------------------------------------------------------------------

class HorarioCreate(BaseModel):
    dia_semana: int = Field(ge=0, le=6)  # 0=lunes … 6=domingo
    hora_apertura: time
    hora_cierre: time

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def apertura_antes_cierre(self) -> "HorarioCreate":
        if self.hora_cierre <= self.hora_apertura:
            raise ValueError("hora_cierre debe ser posterior a hora_apertura")
        return self


class HorarioUpdate(BaseModel):
    hora_apertura: time | None = None
    hora_cierre: time | None = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def apertura_antes_cierre(self) -> "HorarioUpdate":
        if (
            self.hora_apertura is not None
            and self.hora_cierre is not None
            and self.hora_cierre <= self.hora_apertura
        ):
            raise ValueError("hora_cierre debe ser posterior a hora_apertura")
        return self


class HorarioRead(BaseModel):
    id: int
    dia_semana: int
    hora_apertura: time
    hora_cierre: time

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Citas
# ---------------------------------------------------------------------------

class CitaCreate(BaseModel):
    servicio_id: int = Field(gt=0)
    fecha: date
    hora_inicio: time

    model_config = {"extra": "forbid"}  # rechaza cliente_id, estado, hora_fin del body

    @field_validator("hora_inicio")
    @classmethod
    def hora_en_franja(cls, v: time) -> time:
        if v.minute not in {0, 30} or v.second != 0 or v.microsecond != 0:
            raise ValueError("hora_inicio debe estar en punto (:00) o y media (:30), sin segundos")
        return v


class CitaRead(BaseModel):
    id: int
    cliente_id: int
    servicio_id: int
    fecha: date
    hora_inicio: time
    hora_fin: time
    estado: EstadoCita

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Disponibilidad
# ---------------------------------------------------------------------------

class DisponibilidadRead(BaseModel):
    fecha: date
    servicio_id: int
    horas_disponibles: list[time]
