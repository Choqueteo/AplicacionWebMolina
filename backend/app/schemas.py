from datetime import date, time
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models import EstadoCita


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    telefono: str = Field(pattern=r"^\+?[0-9]{9,15}$")
    nombre_completo: str = Field(min_length=1, max_length=100)
    # Sin campo `rol`: el endpoint lo fuerza siempre a 'cliente'

    model_config = {"extra": "forbid"}  # 422 ante cualquier campo extra (anti mass-assignment)


class UsuarioRead(BaseModel):
    id: int
    email: str
    telefono: str
    nombre_completo: str
    rol: str

    model_config = {"from_attributes": True}


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
