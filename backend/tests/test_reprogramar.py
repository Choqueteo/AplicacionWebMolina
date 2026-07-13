"""Tests del endpoint PATCH /citas/{id}/reprogramar."""
from datetime import date, datetime, time, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app.models import (
    Cita, EstadoCita, ExcepcionFecha, FranjaOcupada,
    HorarioPeluquero, Rol, TipoExcepcion, Usuario,
)
from app.security import create_access_token, decode_access_token, hash_password

_MADRID = ZoneInfo("Europe/Madrid")

# Fechas usadas en tests — siempre >24 h desde ahora
_BASE   = date.today() + timedelta(days=2)   # cita inicial: siempre >24 h
_DEST   = date.today() + timedelta(days=3)   # destino de reprogramación


# ---------------------------------------------------------------------------
# Helpers locales
# ---------------------------------------------------------------------------

def _asegurar_horario(db, fecha):
    """Crea tramo 09:00-18:00 para el día de la semana de fecha, si no existe."""
    if not db.query(HorarioPeluquero).filter_by(dia_semana=fecha.weekday()).first():
        db.add(HorarioPeluquero(dia_semana=fecha.weekday(),
                                hora_apertura=time(9, 0), hora_cierre=time(18, 0)))
        db.commit()


def _crear_cliente(db, suffix="b"):
    u = Usuario(
        email=f"cli{suffix}@test.com",
        password_hash=hash_password("x"),
        telefono="600000099",
        nombre_completo=f"Cliente {suffix.upper()} Test",
        rol=Rol.cliente,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _token(usuario):
    return create_access_token(usuario.id, usuario.rol.value)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _uid(token):
    """Extrae user_id del JWT sin llamadas a la API."""
    return int(decode_access_token(token)["sub"])


def _crear_cita_db(db, cliente_id, servicio_id, fecha, hora_inicio, estado=EstadoCita.activa):
    """Inserta cita+franja directamente en BD (bypass API, útil para fechas pasadas/cercanas)."""
    hora_fin = (datetime.combine(date.min, hora_inicio) + timedelta(minutes=30)).time()
    cita = Cita(
        cliente_id=cliente_id, servicio_id=servicio_id,
        fecha=fecha, hora_inicio=hora_inicio, hora_fin=hora_fin,
        estado=estado,
    )
    db.add(cita)
    db.flush()
    db.add(FranjaOcupada(cita_id=cita.id, fecha=fecha, hora=hora_inicio))
    db.commit()
    db.refresh(cita)
    return cita


def _crear_cita_api(client, token, servicio_id, fecha, hora="10:00:00"):
    r = client.post("/citas",
                    json={"servicio_id": servicio_id, "fecha": str(fecha), "hora_inicio": hora},
                    headers=_auth(token))
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _reprogramar(client, token, cita_id, fecha, hora="11:00:00"):
    return client.patch(f"/citas/{cita_id}/reprogramar",
                        json={"fecha": str(fecha), "hora_inicio": hora},
                        headers=_auth(token))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_reprogramar_exitoso(client, db_session, cliente_token, servicio_corte):
    """200: franjas viejas borradas, franjas nuevas creadas, cita actualizada, estado activa."""
    _asegurar_horario(db_session, _BASE)
    _asegurar_horario(db_session, _DEST)

    cita_id = _crear_cita_api(client, cliente_token, servicio_corte.id, _BASE, "10:00:00")

    r = _reprogramar(client, cliente_token, cita_id, _DEST, "11:00:00")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["fecha"] == str(_DEST)
    assert data["hora_inicio"] == "11:00:00"
    assert data["estado"] == "activa"

    # Franja vieja liberada
    assert db_session.query(FranjaOcupada).filter_by(fecha=_BASE, hora=time(10, 0)).first() is None
    # Franja nueva creada
    assert db_session.query(FranjaOcupada).filter_by(cita_id=cita_id, fecha=_DEST, hora=time(11, 0)).first()


def test_reprogramar_libera_franja_para_tercero(client, db_session, cliente_token, servicio_corte):
    """Tras reprogramar, el hueco original queda libre para otra reserva."""
    _asegurar_horario(db_session, _BASE)
    _asegurar_horario(db_session, _DEST)

    cita_id = _crear_cita_api(client, cliente_token, servicio_corte.id, _BASE, "10:00:00")
    _reprogramar(client, cliente_token, cita_id, _DEST, "11:00:00")

    u2 = _crear_cliente(db_session, "ter")
    r = client.post("/citas",
                    json={"servicio_id": servicio_corte.id, "fecha": str(_BASE), "hora_inicio": "10:00:00"},
                    headers=_auth(_token(u2)))
    assert r.status_code == 201


def test_reprogramar_menos_24h_422(client, db_session, cliente_token, servicio_corte):
    """Cita original con menos de 24 h de antelación → 422."""
    ahora = datetime.now(_MADRID)
    fecha_cercana = (ahora + timedelta(hours=23)).date()
    hora_cercana  = (ahora + timedelta(hours=23)).replace(minute=0, second=0, microsecond=0).time()
    # Asegurar que la hora quede en múltiplo de 30
    minuto_redondeado = 0 if hora_cercana.minute < 30 else 30
    hora_cercana = hora_cercana.replace(minute=minuto_redondeado)

    _asegurar_horario(db_session, fecha_cercana)
    # Crear horario amplio para que el slot quepa
    if not db_session.query(HorarioPeluquero).filter_by(dia_semana=fecha_cercana.weekday()).first():
        db_session.add(HorarioPeluquero(dia_semana=fecha_cercana.weekday(),
                                        hora_apertura=time(0, 0), hora_cierre=time(23, 30)))
        db_session.commit()

    cliente_id = _uid(cliente_token)
    cita = _crear_cita_db(db_session, cliente_id, servicio_corte.id, fecha_cercana, hora_cercana)

    _asegurar_horario(db_session, _BASE)
    r = _reprogramar(client, cliente_token, cita.id, _BASE, "10:00:00")
    assert r.status_code == 422
    assert "24" in r.json()["detail"]


def test_reprogramar_hueco_ocupado_409_cita_intacta(client, db_session, cliente_token, servicio_corte):
    """Destino ya ocupado → 409; la cita original conserva su fecha y sus franjas."""
    _asegurar_horario(db_session, _BASE)

    cita_id = _crear_cita_api(client, cliente_token, servicio_corte.id, _BASE, "10:00:00")

    # Cliente B ocupa el destino (11:00)
    u2 = _crear_cliente(db_session, "b2")
    client.post("/citas",
                json={"servicio_id": servicio_corte.id, "fecha": str(_BASE), "hora_inicio": "11:00:00"},
                headers=_auth(_token(u2)))

    r = _reprogramar(client, cliente_token, cita_id, _BASE, "11:00:00")
    assert r.status_code == 409

    # Cita intacta
    cita = db_session.get(Cita, cita_id)
    assert cita.fecha == _BASE
    assert cita.hora_inicio == time(10, 0)
    # Franja original restaurada
    assert db_session.query(FranjaOcupada).filter_by(cita_id=cita_id, fecha=_BASE, hora=time(10, 0)).first()


def test_reprogramar_dia_cerrado_422(client, db_session, cliente_token, servicio_corte):
    """Fecha destino marcada como cerrada → 422."""
    _asegurar_horario(db_session, _BASE)
    _asegurar_horario(db_session, _DEST)
    db_session.add(ExcepcionFecha(fecha=_DEST, tipo=TipoExcepcion.cerrado))
    db_session.commit()

    cita_id = _crear_cita_api(client, cliente_token, servicio_corte.id, _BASE, "10:00:00")

    r = _reprogramar(client, cliente_token, cita_id, _DEST, "10:00:00")
    assert r.status_code == 422
    assert "cerrado" in r.json()["detail"].lower()


def test_reprogramar_fuera_ventana_422(client, db_session, cliente_token, servicio_corte):
    """Fecha destino > hoy+30 → 422."""
    _asegurar_horario(db_session, _BASE)

    cita_id = _crear_cita_api(client, cliente_token, servicio_corte.id, _BASE, "10:00:00")

    fecha_lejana = date.today() + timedelta(days=31)
    r = _reprogramar(client, cliente_token, cita_id, fecha_lejana, "10:00:00")
    assert r.status_code == 422


def test_reprogramar_fuera_horario_422(client, db_session, cliente_token, servicio_corte):
    """Hora fuera del tramo (09:00-18:00) → 422."""
    _asegurar_horario(db_session, _BASE)

    cita_id = _crear_cita_api(client, cliente_token, servicio_corte.id, _BASE, "10:00:00")

    r = _reprogramar(client, cliente_token, cita_id, _BASE, "20:00:00")
    assert r.status_code == 422


def test_reprogramar_otro_usuario_403(client, db_session, cliente_token, servicio_corte):
    """Cliente B intenta reprogramar cita de A → 403."""
    _asegurar_horario(db_session, _BASE)

    cita_id = _crear_cita_api(client, cliente_token, servicio_corte.id, _BASE, "10:00:00")

    u2 = _crear_cliente(db_session, "otro")
    r = _reprogramar(client, _token(u2), cita_id, _BASE, "12:00:00")
    assert r.status_code == 403


def test_reprogramar_admin_puede_ajena(client, db_session, cliente_token, admin_token, servicio_corte):
    """Admin puede reprogramar la cita de cualquier cliente."""
    _asegurar_horario(db_session, _BASE)

    cita_id = _crear_cita_api(client, cliente_token, servicio_corte.id, _BASE, "10:00:00")

    r = _reprogramar(client, admin_token, cita_id, _BASE, "12:00:00")
    assert r.status_code == 200
    assert r.json()["hora_inicio"] == "12:00:00"


def test_reprogramar_cita_cancelada_422(client, db_session, cliente_token, servicio_corte):
    """Cita cancelada → 422."""
    _asegurar_horario(db_session, _BASE)

    cita_id = _crear_cita_api(client, cliente_token, servicio_corte.id, _BASE, "10:00:00")
    client.patch(f"/citas/{cita_id}/cancelar", headers=_auth(cliente_token))

    r = _reprogramar(client, cliente_token, cita_id, _BASE, "12:00:00")
    assert r.status_code == 422


def test_reprogramar_cita_pasada_422(client, db_session, cliente_token, servicio_corte):
    """Cita con fecha de ayer → 422."""
    ayer = date.today() - timedelta(days=1)
    cliente_id = _uid(cliente_token)
    cita = _crear_cita_db(db_session, cliente_id, servicio_corte.id, ayer, time(10, 0))

    _asegurar_horario(db_session, _BASE)
    r = _reprogramar(client, cliente_token, cita.id, _BASE, "10:00:00")
    assert r.status_code == 422


def test_reprogramar_cliente_bloqueado_403(client, db_session, cliente_token, servicio_corte):
    """Cliente bloqueado → 403."""
    _asegurar_horario(db_session, _BASE)

    cita_id = _crear_cita_api(client, cliente_token, servicio_corte.id, _BASE, "10:00:00")

    uid = _uid(cliente_token)
    u = db_session.get(Usuario, uid)
    u.bloqueado = True
    db_session.commit()

    r = _reprogramar(client, cliente_token, cita_id, _BASE, "12:00:00")
    assert r.status_code == 403


def test_reprogramar_telegram_enviado(client, db_session, cliente_token, servicio_corte):
    """Reprogramación exitosa envía 1 mensaje Telegram con 'De:' y 'A:'."""
    _asegurar_horario(db_session, _BASE)
    _asegurar_horario(db_session, _DEST)

    cita_id = _crear_cita_api(client, cliente_token, servicio_corte.id, _BASE, "10:00:00")

    with patch("app.routers.citas.enviar_aviso_peluquero") as mock_tg:
        r = _reprogramar(client, cliente_token, cita_id, _DEST, "11:00:00")

    assert r.status_code == 200
    mock_tg.assert_called_once()
    msg = mock_tg.call_args[0][0]
    assert "De:" in msg
    assert "A:" in msg
