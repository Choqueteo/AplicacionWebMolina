import enum
from datetime import date, time
from decimal import Decimal

from app.constants import DURACION_MAX_MINUTOS, FRANJA_MINUTOS
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------------------------------------------------------------------------
# Enums de dominio
# ---------------------------------------------------------------------------

class Rol(str, enum.Enum):
    admin   = "admin"
    cliente = "cliente"


class EstadoCita(str, enum.Enum):
    activa      = "activa"
    cancelada   = "cancelada"
    no_asistida = "no_asistida"


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------

class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint("rol IN ('admin','cliente')", name="ck_usuario_rol"),
    )

    id              : Mapped[int]  = mapped_column(primary_key=True)
    email           : Mapped[str]  = mapped_column(String(255), unique=True)
    password_hash   : Mapped[str]  = mapped_column(String(255))
    telefono        : Mapped[str]  = mapped_column(String(20))
    nombre_completo : Mapped[str]  = mapped_column(String(100))
    rol             : Mapped[Rol]  = mapped_column(
                          SAEnum(Rol, native_enum=False, length=10)
                      )
    bloqueado       : Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    inasistencias   : Mapped[int]  = mapped_column(Integer, default=0, nullable=False)

    citas: Mapped[list["Cita"]] = relationship(back_populates="cliente")


class Servicio(Base):
    __tablename__ = "servicios"
    __table_args__ = (
        CheckConstraint(
            f"duracion_minutos > 0 AND duracion_minutos <= {DURACION_MAX_MINUTOS} AND mod(duracion_minutos, {FRANJA_MINUTOS}) = 0",
            name="ck_servicio_duracion",
        ),
    )

    id               : Mapped[int]     = mapped_column(primary_key=True)
    nombre           : Mapped[str]     = mapped_column(String(100))
    duracion_minutos : Mapped[int]     = mapped_column(Integer)
    precio           : Mapped[Decimal] = mapped_column(Numeric(8, 2))
    activo           : Mapped[bool]    = mapped_column(Boolean, default=True, nullable=False)

    citas: Mapped[list["Cita"]] = relationship(back_populates="servicio")


class HorarioPeluquero(Base):
    __tablename__ = "horario_peluquero"
    __table_args__ = (
        CheckConstraint("hora_apertura < hora_cierre", name="ck_horario_rango"),
    )

    id            : Mapped[int]  = mapped_column(primary_key=True)
    # 0 = lunes … 6 = domingo  (convención date.weekday())
    dia_semana    : Mapped[int]  = mapped_column(SmallInteger)
    hora_apertura : Mapped[time] = mapped_column(Time)
    hora_cierre   : Mapped[time] = mapped_column(Time)


class Cita(Base):
    __tablename__ = "citas"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('activa','cancelada','no_asistida')", name="ck_cita_estado"
        ),
    )

    id          : Mapped[int]        = mapped_column(primary_key=True)
    cliente_id  : Mapped[int]        = mapped_column(ForeignKey("usuarios.id"))
    servicio_id : Mapped[int]        = mapped_column(ForeignKey("servicios.id"))
    fecha       : Mapped[date]       = mapped_column(Date)
    hora_inicio : Mapped[time]       = mapped_column(Time)
    hora_fin    : Mapped[time]       = mapped_column(Time)
    # hora_fin = hora_inicio + servicio.duracion_minutos; calculado en capa de servicio
    estado      : Mapped[EstadoCita] = mapped_column(
                      SAEnum(EstadoCita, native_enum=False, length=15),
                      default=EstadoCita.activa,
                  )

    cliente  : Mapped["Usuario"]             = relationship(back_populates="citas")
    servicio : Mapped["Servicio"]            = relationship(back_populates="citas")
    franjas  : Mapped[list["FranjaOcupada"]] = relationship(back_populates="cita")


class FranjaOcupada(Base):
    __tablename__ = "franja_ocupada"
    __table_args__ = (
        UniqueConstraint("fecha", "hora", name="uq_franja_fecha_hora"),
    )

    id      : Mapped[int]  = mapped_column(primary_key=True)
    # ondelete CASCADE: red de seguridad si alguna cita se borrara por error
    cita_id : Mapped[int]  = mapped_column(ForeignKey("citas.id", ondelete="CASCADE"))
    fecha   : Mapped[date] = mapped_column(Date)
    hora    : Mapped[time] = mapped_column(Time)

    cita: Mapped["Cita"] = relationship(back_populates="franjas")


class TipoExcepcion(str, enum.Enum):
    cerrado = "cerrado"
    # Futuro: horario_especial = "horario_especial"


class ExcepcionFecha(Base):
    __tablename__ = "excepcion_fecha"
    __table_args__ = (
        UniqueConstraint("fecha", name="uq_excepcion_fecha"),
    )

    id    : Mapped[int]           = mapped_column(primary_key=True)
    fecha : Mapped[date]          = mapped_column(Date)
    tipo  : Mapped[TipoExcepcion] = mapped_column(
                SAEnum(TipoExcepcion, native_enum=False, length=20),
                default=TipoExcepcion.cerrado,
            )
