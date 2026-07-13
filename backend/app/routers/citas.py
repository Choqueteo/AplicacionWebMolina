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
from app.schemas import CitaCreate, CitaRead, CitaReprogramar
from app.security import decode_access_token

router = APIRouter(tags=["citas"])

_MADRID = ZoneInfo("Europe/Madrid")


# ---------------------------------------------------------------------------
# Helpers privados — reutilizados en POST /citas y PATCH /reprogramar
# ---------------------------------------------------------------------------

def _generar_franjas(fecha: date, hora_inicio, duracion_minutos: int) -> list:
    """Lista de (fecha, hora) para cada franja de 30 min del servicio."""
    franjas, cursor = [], datetime.combine(fecha, hora_inicio)
    for _ in range(duracion_minutos // FRANJA_MINUTOS):
        franjas.append((fecha, cursor.time()))
        cursor += timedelta(minutes=FRANJA_MINUTOS)
    return franjas


def _validar_slot(db, servicio, fecha: date, hora_inicio, today_madrid: date, now_madrid: datetime) -> None:
    """
    Valida ventana de reserva, día cerrado, horario y encaje de la duración.
    NO consulta FranjaOcupada — el solape lo detecta el INSERT + IntegrityError.
    Lanza HTTPException(422) si alguna condición falla.
    """
    if fecha < today_madrid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se pueden reservar citas en fechas pasadas",
        )
    if fecha > today_madrid + timedelta(days=DIAS_MAX_RESERVA):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Solo se pueden reservar citas con un máximo de {DIAS_MAX_RESERVA} días de antelación",
        )
    if db.query(ExcepcionFecha).filter_by(fecha=fecha, tipo=TipoExcepcion.cerrado).first():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ese día está cerrado y no admite reservas",
        )
    tramos = (
        db.query(HorarioPeluquero)
        .filter_by(dia_semana=fecha.weekday())
        .order_by(HorarioPeluquero.hora_apertura)
        .all()
    )
    if not tramos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No hay horario definido para ese día de la semana",
        )
    hora_fin = (
        datetime.combine(date.min, hora_inicio) + timedelta(minutes=servicio.duracion_minutos)
    ).time()
    if not any(hora_inicio >= t.hora_apertura and hora_fin <= t.hora_cierre for t in tramos):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La cita queda fuera del horario de apertura",
        )
    if fecha == today_madrid and hora_inicio <= now_madrid.time():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La hora indicada ya ha pasado",
        )


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

    # 2–5. Validar ventana, día cerrado, horario y encaje
    _validar_slot(db, servicio, datos.fecha, datos.hora_inicio, today_madrid, now_madrid)

    hora_fin = (
        datetime.combine(date.min, datos.hora_inicio)
        + timedelta(minutes=servicio.duracion_minutos)
    ).time()

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

        for fecha_f, hora_f in _generar_franjas(datos.fecha, datos.hora_inicio, servicio.duracion_minutos):
            db.add(FranjaOcupada(cita_id=cita.id, fecha=fecha_f, hora=hora_f))

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


@router.patch("/citas/{cita_id}/reprogramar", response_model=CitaRead)
def reprogramar_cita(
    cita_id: int,
    background_tasks: BackgroundTasks,
    datos: CitaReprogramar,
    usuario: Usuario = Depends(get_usuario_actual),
    db: Session = Depends(get_db),
):
    """
    Cambia fecha/hora de una cita activa y futura (mismo servicio).
    Transacción atómica: borra franjas viejas + crea nuevas + actualiza la cita.
    Si el nuevo hueco está ocupado → IntegrityError → rollback → 409 (cita intacta).
    """
    # 1. Existe
    cita = db.get(Cita, cita_id)
    if cita is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")

    # 2. Solo dueño o admin — 403 (no 404) según spec de reprogramar
    if usuario.rol != Rol.admin and cita.cliente_id != usuario.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para reprogramar esta cita")

    # 3. Solo citas activas
    if cita.estado != EstadoCita.activa:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solo se pueden reprogramar citas activas",
        )

    now_madrid = datetime.now(_MADRID)
    today_madrid = now_madrid.date()

    # 4. Cita no pasada
    cita_dt = datetime.combine(cita.fecha, cita.hora_inicio).replace(tzinfo=_MADRID)
    if cita_dt <= now_madrid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se pueden reprogramar citas pasadas",
        )

    # 5. Antelación mínima 24 h sobre la cita ORIGINAL
    if (cita_dt - now_madrid).total_seconds() < 24 * 3600:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solo se puede reprogramar con al menos 24 h de antelación",
        )

    # 6. Cliente no bloqueado
    if cita.cliente.bloqueado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta está bloqueada. Contacta con el peluquero.",
        )

    # 7. Validar el nuevo hueco (ventana, día cerrado, horario, encaje)
    servicio = db.get(Servicio, cita.servicio_id)
    _validar_slot(db, servicio, datos.fecha, datos.hora_inicio, today_madrid, now_madrid)

    nueva_hora_fin = (
        datetime.combine(datos.fecha, datos.hora_inicio)
        + timedelta(minutes=servicio.duracion_minutos)
    ).time()

    # Guardar datos actuales para el mensaje Telegram
    fecha_ant = cita.fecha
    hora_ant  = cita.hora_inicio

    # 8. Transacción atómica
    try:
        db.query(FranjaOcupada).filter(
            FranjaOcupada.cita_id == cita.id
        ).delete(synchronize_session="fetch")

        cita.fecha       = datos.fecha
        cita.hora_inicio = datos.hora_inicio
        cita.hora_fin    = nueva_hora_fin

        for fecha_f, hora_f in _generar_franjas(datos.fecha, datos.hora_inicio, servicio.duracion_minutos):
            db.add(FranjaOcupada(cita_id=cita.id, fecha=fecha_f, hora=hora_f))

        db.flush()
        db.commit()
        db.refresh(cita)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ese hueco se acaba de ocupar; elige otro.",
        )

    cliente = db.get(Usuario, cita.cliente_id)
    mensaje = (
        f"Cita reprogramada por el cliente\n"
        f"Cliente: {cliente.nombre_completo} | {cliente.telefono}\n"
        f"Servicio: {servicio.nombre}\n"
        f"De: {fecha_ant.strftime('%d/%m/%Y')} a las {hora_ant.strftime('%H:%M')}\n"
        f"A: {datos.fecha.strftime('%d/%m/%Y')} a las {datos.hora_inicio.strftime('%H:%M')}"
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
