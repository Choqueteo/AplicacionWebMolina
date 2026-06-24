from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app.constants import DIAS_MAX_RESERVA
from app.models import (
    Cita,
    EstadoCita,
    ExcepcionFecha,
    HorarioPeluquero,
    Rol,
    Servicio,
    TipoExcepcion,
    Usuario,
)
from app.security import create_access_token, hash_password

_MADRID = ZoneInfo("Europe/Madrid")


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hoy_madrid() -> date:
    return datetime.now(_MADRID).date()


def _crear_excepcion(db_session, fecha: date) -> ExcepcionFecha:
    exc = ExcepcionFecha(fecha=fecha, tipo=TipoExcepcion.cerrado)
    db_session.add(exc)
    db_session.commit()
    db_session.refresh(exc)
    return exc


def _horario_para(db_session, fecha: date) -> HorarioPeluquero:
    h = HorarioPeluquero(
        dia_semana=fecha.weekday(),
        hora_apertura=time(9, 0),
        hora_cierre=time(18, 0),
    )
    db_session.add(h)
    db_session.commit()
    db_session.refresh(h)
    return h


def _servicio(db_session) -> Servicio:
    s = Servicio(nombre="Corte test", duracion_minutos=30, precio=Decimal("15.00"), activo=True)
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


def _cita_activa(db_session, usuario_id: int, servicio_id: int, fecha: date) -> Cita:
    c = Cita(
        cliente_id=usuario_id,
        servicio_id=servicio_id,
        fecha=fecha,
        hora_inicio=time(10, 0),
        hora_fin=time(10, 30),
        estado=EstadoCita.activa,
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


def _usuario_cliente(db_session, suffix: str = "") -> tuple[Usuario, str]:
    u = Usuario(
        email=f"cli{suffix}@exc.test",
        password_hash=hash_password("x"),
        telefono="600000099",
        nombre_completo="Cliente Exc",
        rol=Rol.cliente,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u, create_access_token(u.id, u.rol.value)


# ---------------------------------------------------------------------------
# Tests de endpoints de excepciones
# ---------------------------------------------------------------------------

def test_listar_vacio(client, admin_token):
    r = client.get("/excepciones", headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.json() == []


def test_anadir_admin_201(client, admin_token):
    fecha = str(_hoy_madrid() + timedelta(days=5))
    r = client.post("/excepciones", json={"fecha": fecha}, headers=_auth(admin_token))
    assert r.status_code == 201
    data = r.json()
    assert data["fecha"] == fecha
    assert data["tipo"] == "cerrado"
    assert "id" in data


def test_anadir_cliente_403(client, cliente_token):
    fecha = str(_hoy_madrid() + timedelta(days=5))
    r = client.post("/excepciones", json={"fecha": fecha}, headers=_auth(cliente_token))
    assert r.status_code == 403


def test_anadir_duplicado_409(client, admin_token):
    fecha = str(_hoy_madrid() + timedelta(days=6))
    client.post("/excepciones", json={"fecha": fecha}, headers=_auth(admin_token))
    r = client.post("/excepciones", json={"fecha": fecha}, headers=_auth(admin_token))
    assert r.status_code == 409
    assert "cerrada" in r.json()["detail"].lower()


def test_anadir_con_cita_activa_409(client, admin_token, db_session):
    hoy = _hoy_madrid()
    fecha = hoy + timedelta(days=7)
    s = _servicio(db_session)
    u, _ = _usuario_cliente(db_session, "a")
    _cita_activa(db_session, u.id, s.id, fecha)

    r = client.post("/excepciones", json={"fecha": str(fecha)}, headers=_auth(admin_token))
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert "1" in detail
    assert "cita" in detail.lower()


def test_anadir_con_cita_cancelada_ok(client, admin_token, db_session):
    hoy = _hoy_madrid()
    fecha = hoy + timedelta(days=8)
    s = _servicio(db_session)
    u, _ = _usuario_cliente(db_session, "b")
    cita = _cita_activa(db_session, u.id, s.id, fecha)
    cita.estado = EstadoCita.cancelada
    db_session.commit()

    r = client.post("/excepciones", json={"fecha": str(fecha)}, headers=_auth(admin_token))
    assert r.status_code == 201


def test_eliminar_admin_200(client, admin_token, db_session):
    fecha = _hoy_madrid() + timedelta(days=9)
    exc = _crear_excepcion(db_session, fecha)

    r = client.delete(f"/excepciones/{exc.id}", headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.json()["id"] == exc.id

    # Confirmamos que ya no existe
    r2 = client.get("/excepciones", headers=_auth(admin_token))
    ids = [e["id"] for e in r2.json()]
    assert exc.id not in ids


def test_eliminar_id_inexistente_404(client, admin_token):
    r = client.delete("/excepciones/99999", headers=_auth(admin_token))
    assert r.status_code == 404
    assert "encontrada" in r.json()["detail"].lower()


def test_proximas_en_ventana(client, cliente_token, db_session):
    hoy = _hoy_madrid()

    # Dentro de la ventana
    fecha_dentro = hoy + timedelta(days=3)
    _crear_excepcion(db_session, fecha_dentro)

    # Fuera de la ventana (mañana de hoy+30)
    fecha_fuera = hoy + timedelta(days=DIAS_MAX_RESERVA + 1)
    _crear_excepcion(db_session, fecha_fuera)

    r = client.get("/excepciones/proximas", headers=_auth(cliente_token))
    assert r.status_code == 200
    fechas = [e["fecha"] for e in r.json()]
    assert str(fecha_dentro) in fechas
    assert str(fecha_fuera) not in fechas


# ---------------------------------------------------------------------------
# Integración: disponibilidad y citas con fecha cerrada
# ---------------------------------------------------------------------------

def test_disponibilidad_fecha_cerrada_vacia(client, cliente_token, db_session):
    """Fecha cerrada con horario configurado → horas_disponibles vacías."""
    hoy = _hoy_madrid()
    fecha = hoy + timedelta(days=2)
    _horario_para(db_session, fecha)
    s = _servicio(db_session)
    _crear_excepcion(db_session, fecha)

    r = client.get(
        "/disponibilidad",
        params={"fecha": str(fecha), "servicio_id": s.id},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    assert r.json()["horas_disponibles"] == []


def test_cita_fecha_cerrada_422(client, cliente_token, db_session):
    """POST /citas con fecha cerrada → 422 con 'cerrado' en el mensaje."""
    hoy = _hoy_madrid()
    fecha = hoy + timedelta(days=2)
    _horario_para(db_session, fecha)
    s = _servicio(db_session)
    _crear_excepcion(db_session, fecha)

    r = client.post(
        "/citas",
        json={"servicio_id": s.id, "fecha": str(fecha), "hora_inicio": "10:00:00"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422
    assert "cerrado" in r.json()["detail"].lower()


def test_hoy_cerrado_disponibilidad(client, cliente_token, db_session):
    """Cerrar hoy (Europe/Madrid) con horario → disponibilidad vacía (cubre timezone)."""
    hoy = _hoy_madrid()
    _horario_para(db_session, hoy)
    s = _servicio(db_session)
    _crear_excepcion(db_session, hoy)

    r = client.get(
        "/disponibilidad",
        params={"fecha": str(hoy), "servicio_id": s.id},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    assert r.json()["horas_disponibles"] == []


def test_hoy_cerrado_cita_422(client, cliente_token, db_session):
    """Cerrar hoy → POST /citas devuelve 422 por excepción (no por hora pasada)."""
    hoy = _hoy_madrid()
    _horario_para(db_session, hoy)
    s = _servicio(db_session)
    _crear_excepcion(db_session, hoy)

    # Hora futura (23:00) para que no falle por "hora pasada" antes del check de excepción
    r = client.post(
        "/citas",
        json={"servicio_id": s.id, "fecha": str(hoy), "hora_inicio": "23:00:00"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422
    assert "cerrado" in r.json()["detail"].lower()
