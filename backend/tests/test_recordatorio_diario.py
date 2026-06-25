"""Tests del script de recordatorio diario."""
from datetime import date, datetime, time, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app.models import Cita, EstadoCita, Rol, Usuario
from app.security import hash_password
from scripts.recordatorio_diario import enviar_recordatorio

_MADRID = ZoneInfo("Europe/Madrid")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _crear_cliente(db, suffix=""):
    u = Usuario(
        email=f"rec{suffix}@test.com",
        password_hash=hash_password("x"),
        telefono="600000099",
        nombre_completo=f"Cliente Rec {suffix}",
        rol=Rol.cliente,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _crear_cita(db, cliente_id, servicio_id, fecha, hora, estado=EstadoCita.activa):
    c = Cita(
        cliente_id=cliente_id,
        servicio_id=servicio_id,
        fecha=fecha,
        hora_inicio=hora,
        hora_fin=(datetime.combine(date.min, hora) + timedelta(minutes=30)).time(),
        estado=estado,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_con_citas_activas_mensaje_correcto(db_session, servicio_corte):
    """2 citas activas mañana → mensaje contiene hora y nombre en orden."""
    manana = date.today() + timedelta(days=1)
    c1 = _crear_cliente(db_session, "1")
    c2 = _crear_cliente(db_session, "2")
    _crear_cita(db_session, c1.id, servicio_corte.id, manana, time(10, 0))
    _crear_cita(db_session, c2.id, servicio_corte.id, manana, time(11, 0))

    with patch("scripts.recordatorio_diario.enviar_aviso_peluquero") as mock_fn:
        enviar_recordatorio(db=db_session, _manana=manana)

    mock_fn.assert_called_once()
    mensaje = mock_fn.call_args[0][0]
    assert "10:00" in mensaje
    assert c1.nombre_completo in mensaje
    assert "11:00" in mensaje
    assert c2.nombre_completo in mensaje
    assert mensaje.index("10:00") < mensaje.index("11:00")


def test_sin_citas_mensaje_indicarlo(db_session):
    """Sin citas → mensaje contiene 'no tienes citas' y la fecha DD/MM."""
    manana = date.today() + timedelta(days=1)

    with patch("scripts.recordatorio_diario.enviar_aviso_peluquero") as mock_fn:
        enviar_recordatorio(db=db_session, _manana=manana)

    mock_fn.assert_called_once()
    mensaje = mock_fn.call_args[0][0]
    assert "no tienes citas" in mensaje.lower()
    assert manana.strftime("%d/%m") in mensaje


def test_citas_canceladas_no_aparecen(db_session, servicio_corte):
    """Cita cancelada mañana → el nombre del cliente NO aparece en el mensaje."""
    manana = date.today() + timedelta(days=1)
    cliente = _crear_cliente(db_session, "canc")
    _crear_cita(
        db_session, cliente.id, servicio_corte.id, manana, time(10, 0),
        estado=EstadoCita.cancelada,
    )

    with patch("scripts.recordatorio_diario.enviar_aviso_peluquero") as mock_fn:
        enviar_recordatorio(db=db_session, _manana=manana)

    mensaje = mock_fn.call_args[0][0]
    assert cliente.nombre_completo not in mensaje


def test_calculo_manana_en_madrid(db_session):
    """'Mañana' se calcula en Europe/Madrid: 22:00 del 30/06 → mensaje contiene '01/07'."""
    with patch("scripts.recordatorio_diario.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 6, 30, 22, 0, tzinfo=_MADRID)
        with patch("scripts.recordatorio_diario.enviar_aviso_peluquero") as mock_fn:
            enviar_recordatorio(db=db_session)

    assert mock_fn.call_count == 1
    assert "01/07" in mock_fn.call_args[0][0]


def test_exactamente_un_mensaje(db_session, servicio_corte):
    """Con 3 citas activas, se envía exactamente 1 mensaje (no uno por cita)."""
    manana = date.today() + timedelta(days=1)
    for i in range(3):
        c = _crear_cliente(db_session, str(i))
        _crear_cita(db_session, c.id, servicio_corte.id, manana, time(9 + i, 0))

    with patch("scripts.recordatorio_diario.enviar_aviso_peluquero") as mock_fn:
        enviar_recordatorio(db=db_session, _manana=manana)

    assert mock_fn.call_count == 1
