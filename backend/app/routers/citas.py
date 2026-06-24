from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants import DIAS_MAX_RESERVA, FRANJA_MINUTOS
from app.database import get_db
from app.dependencies import get_usuario_actual, solo_admin
from app.models import Cita, EstadoCita, ExcepcionFecha, FranjaOcupada, HorarioPeluquero, Rol, Servicio, TipoExcepcion, Usuario
from app.notificaciones.telegram import enviar_aviso_peluquero
from app.rate_limit import get_real_ip, limiter
from app.schemas import CitaCreate, CitaRead
from app.security import decode_access_token

router = APIRouter(tags=["citas"])

_MADRID = ZoneInfo("Europe/Madrid")


def _key_usuario(request: Request) -> str:
    """Rate-limit key por user_id del JWT; fallback a IP si el token no es válido."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload = decode_access_token(auth.split(" ")[1])
            return f"user:{payload['sub']}"
        except Exception:
            pass
    return get_real_ip(request)


# ---------------------------------------------------------------------------
# Rutas — literales antes que rutas con parámetro (CLAUDE.md)
# ---------------------------------------------------------------------------

@router.get("/citas", response_model=list[CitaRead])
def listar_citas(
    fecha: date | None = None,
    _: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """Agenda completa. Solo admin. ?fecha=YYYY-MM-DD filtra por día."""
    q = db.query(Cita).order_by(Cita.fecha, Cita.hora_inicio)
    if fecha:
        q = q.filter(Cita.fecha == fecha)
    return q.all()


@router.get("/citas/mias", response_model=list[CitaRead])
def mis_citas(
    usuario: Usuario = Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    """Citas del cliente autenticado, ordenadas cronológicamente."""
    return (
        db.query(Cita)
        .filter(Cita.cliente_id == usuario.id)
        .order_by(Cita.fecha, Cita.hora_inicio)
        .all()
    )


@router.post("/citas", response_model=CitaRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute", key_func=_key_usuario)
@limiter.limit("50/day", key_func=_key_usuario)
def crear_cita(
    request: Request,  # requerido por slowapi
    background_tasks: BackgroundTasks,
    datos: CitaCreate,
    usuario: Usuario = Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    """
    Reserva una cita. El cliente_id se extrae del token; nunca del body.
    Transacción atómica: Cita + N FranjaOcupada. Si alguna franja ya existe → 409.
    """
    now_madrid = datetime.now(_MADRID)
    today_madrid = now_madrid.date()

    # 1. Servicio activo
    servicio = db.get(Servicio, datos.servicio_id)
    if not servicio or not servicio.activo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Servicio no encontrado o inactivo",
        )

    # 1b. Cliente no bloqueado
    if usuario.bloqueado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta está bloqueada. Contacta con el peluquero.",
        )

    # 2. Fecha dentro de la ventana de reserva [hoy, hoy+DIAS_MAX_RESERVA]
    if datos.fecha < today_madrid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se pueden reservar citas en fechas pasadas",
        )
    if datos.fecha > today_madrid + timedelta(days=DIAS_MAX_RESERVA):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Solo se pueden reservar citas con un máximo de {DIAS_MAX_RESERVA} días de antelación",
        )

    # 2b. Fecha cerrada → 422
    if db.query(ExcepcionFecha).filter_by(fecha=datos.fecha, tipo=TipoExcepcion.cerrado).first():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ese día está cerrado y no admite reservas",
        )

    # 3. Horario del día (todos los tramos)
    tramos = (
        db.query(HorarioPeluquero)
        .filter_by(dia_semana=datos.fecha.weekday())
        .order_by(HorarioPeluquero.hora_apertura)
        .all()
    )
    if not tramos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No hay horario definido para ese día de la semana",
        )

    # 4. Servicio cabe dentro de algún tramo del día
    hora_fin = (
        datetime.combine(date.min, datos.hora_inicio)
        + timedelta(minutes=servicio.duracion_minutos)
    ).time()

    cabe = any(
        datos.hora_inicio >= tramo.hora_apertura and hora_fin <= tramo.hora_cierre
        for tramo in tramos
    )
    if not cabe:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La cita queda fuera del horario de apertura",
        )

    # 5. Hora no pasada para citas de hoy
    if datos.fecha == today_madrid and datos.hora_inicio <= now_madrid.time():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La hora indicada ya ha pasado",
        )

    # 6. Transacción atómica: Cita + FranjaOcupada
    try:
        cita = Cita(
            cliente_id=usuario.id,
            servicio_id=datos.servicio_id,
            fecha=datos.fecha,
            hora_inicio=datos.hora_inicio,
            hora_fin=hora_fin,
            estado=EstadoCita.activa,
        )
        db.add(cita)
        db.flush()  # obtiene cita.id sin confirmar

        N = servicio.duracion_minutos // FRANJA_MINUTOS
        for i in range(N):
            franja_hora = (
                datetime.combine(date.min, datos.hora_inicio) + timedelta(minutes=FRANJA_MINUTOS * i)
            ).time()
            db.add(FranjaOcupada(cita_id=cita.id, fecha=datos.fecha, hora=franja_hora))

        db.commit()
        db.refresh(cita)

        fecha_str = cita.fecha.strftime("%d/%m/%Y")
        hora_str  = cita.hora_inicio.strftime("%H:%M")
        mensaje = (
            f"Nueva reserva\n"
            f"Cliente: {usuario.nombre_completo} | {usuario.telefono}\n"
            f"Servicio: {servicio.nombre}\n"
            f"Fecha: {fecha_str} a las {hora_str}"
        )
        background_tasks.add_task(enviar_aviso_peluquero, mensaje)
        return cita

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Una o más franjas ya están ocupadas. Recarga la disponibilidad e inténtalo de nuevo.",
        )


@router.get("/citas/{cita_id}", response_model=CitaRead)
def obtener_cita(
    cita_id: int,
    usuario: Usuario = Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    """
    Detalle de una cita. Solo el dueño o un admin pueden verla.
    Se devuelve 404 (no 403) si el usuario no es el dueño, para no revelar existencia (anti-IDOR).
    """
    cita = db.get(Cita, cita_id)
    if cita is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    if usuario.rol != Rol.admin and cita.cliente_id != usuario.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    return cita


@router.patch("/citas/{cita_id}/cancelar", response_model=CitaRead)
def cancelar_cita(
    cita_id: int,
    background_tasks: BackgroundTasks,
    usuario: Usuario = Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    """
    Cancela una cita: pone estado='cancelada' y borra sus FranjaOcupada (libera huecos).
    La fila de Cita se conserva como histórico.
    Solo el dueño o un admin pueden cancelar. 404 para no-dueño (anti-IDOR).
    """
    # 1. Existe
    cita = db.get(Cita, cita_id)
    if cita is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")

    # 2. Autorización por objeto — 404 para no revelar existencia (anti-IDOR)
    if usuario.rol != Rol.admin and cita.cliente_id != usuario.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")

    # 3. Ya cancelada
    if cita.estado == EstadoCita.cancelada:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La cita ya está cancelada")

    # 4. Cita pasada (fecha anterior, o hoy pero la hora ya pasó)
    now_madrid = datetime.now(_MADRID)
    today_madrid = now_madrid.date()
    es_pasada = cita.fecha < today_madrid or (
        cita.fecha == today_madrid and cita.hora_inicio <= now_madrid.time()
    )
    if es_pasada:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se pueden cancelar citas pasadas",
        )

    # 5. Transacción: cambiar estado + liberar franjas
    cita.estado = EstadoCita.cancelada
    db.query(FranjaOcupada).filter(
        FranjaOcupada.cita_id == cita.id
    ).delete(synchronize_session="fetch")
    db.commit()
    db.refresh(cita)

    if usuario.rol != Rol.admin:
        servicio = db.get(Servicio, cita.servicio_id)
        nombre_servicio = servicio.nombre if servicio else f"Servicio #{cita.servicio_id}"
        fecha_str = cita.fecha.strftime("%d/%m/%Y")
        hora_str  = cita.hora_inicio.strftime("%H:%M")
        mensaje = (
            f"Cita cancelada por el cliente\n"
            f"Cliente: {usuario.nombre_completo} | {usuario.telefono}\n"
            f"Servicio: {nombre_servicio}\n"
            f"Fecha: {fecha_str} a las {hora_str}"
        )
        background_tasks.add_task(enviar_aviso_peluquero, mensaje)

    return cita


@router.patch("/citas/{cita_id}/no-asistida", response_model=CitaRead)
def marcar_no_asistida(
    cita_id: int,
    admin: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Marca una cita pasada como 'no_asistida'. Solo admin.
    La FranjaOcupada no se toca: la cita ya es pasada y las franjas no tienen efecto.
    """
    # 1. Existe
    cita = db.get(Cita, cita_id)
    if cita is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")

    # 2. Estado debe ser 'activa'
    if cita.estado != EstadoCita.activa:
        detail = (
            "La cita ya está marcada como no asistida"
            if cita.estado == EstadoCita.no_asistida
            else "La cita está cancelada, no se puede marcar como no asistida"
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    # 3. Cita debe ser pasada
    now_madrid = datetime.now(_MADRID)
    today_madrid = now_madrid.date()
    es_pasada = cita.fecha < today_madrid or (
        cita.fecha == today_madrid and cita.hora_inicio <= now_madrid.time()
    )
    if not es_pasada:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solo se pueden marcar como no asistidas citas que ya hayan pasado",
        )

    cita.estado = EstadoCita.no_asistida
    cita.cliente.inasistencias += 1
    db.commit()
    db.refresh(cita)
    return cita
