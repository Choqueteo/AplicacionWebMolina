from datetime import date, time, timedelta
from zoneinfo import ZoneInfo

from app.constants import DIAS_MAX_RESERVA
from app.models import FranjaOcupada, HorarioPeluquero

_MADRID = ZoneInfo("Europe/Madrid")


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_disponibilidad_dia_con_horario(client, cliente_token, servicio_corte, horario_dia, fecha_test):
    """Día con horario 09:00-18:00 y servicio de 30 min → slots cada 15 min de 09:00 a 17:30."""
    r = client.get(
        "/disponibilidad",
        params={"fecha": str(fecha_test), "servicio_id": servicio_corte.id},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["servicio_id"] == servicio_corte.id
    horas = data["horas_disponibles"]
    # Corte 30 min: primer slot 09:00, último 17:30 (17:30 + 30min = 18:00 = cierre ✓)
    assert "09:00:00" in horas
    assert "09:15:00" in horas   # con franjas de 15 min también hay inicio en :15
    assert "17:30:00" in horas
    assert "17:45:00" not in horas  # 17:45 + 30min = 18:15 > cierre ✗
    assert "18:00:00" not in horas  # 18:00 + 30min sobrepasa el cierre


def test_disponibilidad_dia_sin_horario(client, cliente_token, servicio_corte, fecha_test):
    """Día sin horario configurado → lista vacía (no crea horario en este test)."""
    r = client.get(
        "/disponibilidad",
        params={"fecha": str(fecha_test), "servicio_id": servicio_corte.id},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    assert r.json()["horas_disponibles"] == []


def test_disponibilidad_60min_no_cabe_ultimo_slot(client, cliente_token, servicio_tinte, horario_dia, fecha_test):
    """
    Tinte de 60 min con cierre a las 18:00:
    - 17:00 sí cabe (17:00 + 60min = 18:00 = cierre ✓)
    - 17:15 NO cabe (17:15 + 60min = 18:15 > cierre ✗)
    - 17:30 NO cabe (17:30 + 60min = 18:30 > cierre ✗)
    """
    r = client.get(
        "/disponibilidad",
        params={"fecha": str(fecha_test), "servicio_id": servicio_tinte.id},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    horas = r.json()["horas_disponibles"]
    assert "17:00:00" in horas
    assert "17:15:00" not in horas
    assert "17:30:00" not in horas


def test_disponibilidad_excluye_franja_ocupada(client, cliente_token, db_session, servicio_corte, horario_dia, fecha_test):
    """
    Insertar una FranjaOcupada directamente en BD → ese slot desaparece del resultado.
    Necesitamos una cita FK válida, así que creamos también la cita.
    """
    from decimal import Decimal
    from app.models import Cita, EstadoCita, Usuario, Rol
    from app.security import hash_password

    # Crear un usuario dueño de la cita
    dueno = Usuario(
        email="dueno@test.com",
        password_hash=hash_password("x"),
        telefono="600000099",
        nombre_completo="Dueño",
        rol=Rol.cliente,
    )
    db_session.add(dueno)
    db_session.flush()

    cita = Cita(
        cliente_id=dueno.id,
        servicio_id=servicio_corte.id,
        fecha=fecha_test,
        hora_inicio=time(10, 0),
        hora_fin=time(10, 30),
        estado=EstadoCita.activa,
    )
    db_session.add(cita)
    db_session.flush()

    franja = FranjaOcupada(cita_id=cita.id, fecha=fecha_test, hora=time(10, 0))
    db_session.add(franja)
    db_session.commit()

    r = client.get(
        "/disponibilidad",
        params={"fecha": str(fecha_test), "servicio_id": servicio_corte.id},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    horas = r.json()["horas_disponibles"]
    assert "10:00:00" not in horas
    assert "09:30:00" in horas   # slot anterior sigue libre
    assert "10:30:00" in horas   # slot posterior sigue libre


def test_disponibilidad_15min(client, cliente_token, servicio_barba, horario_dia, fecha_test):
    """Barba de 15 min (1 franja): slots cada 15 min de 09:00 a 17:45."""
    r = client.get(
        "/disponibilidad",
        params={"fecha": str(fecha_test), "servicio_id": servicio_barba.id},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    horas = r.json()["horas_disponibles"]
    assert "09:00:00" in horas
    assert "09:15:00" in horas
    assert "17:45:00" in horas   # 17:45 + 15min = 18:00 = cierre ✓
    assert "18:00:00" not in horas  # 18:00 + 15min > cierre ✗


def test_disponibilidad_45min(client, cliente_token, servicio_corteybarba, horario_dia, fecha_test):
    """Corte y barba de 45 min (3 franjas): último inicio 17:15 (17:15+45=18:00 ✓)."""
    r = client.get(
        "/disponibilidad",
        params={"fecha": str(fecha_test), "servicio_id": servicio_corteybarba.id},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    horas = r.json()["horas_disponibles"]
    assert "09:00:00" in horas
    assert "17:15:00" in horas   # 17:15 + 45min = 18:00 = cierre ✓
    assert "17:30:00" not in horas  # 17:30 + 45min = 18:15 > cierre ✗


# ---------------------------------------------------------------------------
# Ventana de reserva [hoy, hoy+DIAS_MAX_RESERVA]
# ---------------------------------------------------------------------------

def test_disponibilidad_limite_30_ok(client, cliente_token, servicio_corte, db_session):
    """Fecha = hoy+30 (límite inclusive) con horario → devuelve horas disponibles."""
    from datetime import datetime
    hoy_madrid = datetime.now(_MADRID).date()
    fecha_limite = hoy_madrid + timedelta(days=DIAS_MAX_RESERVA)

    # Crear horario para el día de semana de fecha_limite
    h = HorarioPeluquero(
        dia_semana=fecha_limite.weekday(),
        hora_apertura=time(9, 0),
        hora_cierre=time(18, 0),
    )
    db_session.add(h)
    db_session.commit()

    r = client.get(
        "/disponibilidad",
        params={"fecha": str(fecha_limite), "servicio_id": servicio_corte.id},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    assert r.json()["horas_disponibles"] != []


def test_disponibilidad_limite_31_vacio(client, cliente_token, servicio_corte):
    """Fecha = hoy+31 (fuera de ventana) → horas_disponibles vacías, sin error."""
    from datetime import datetime
    hoy_madrid = datetime.now(_MADRID).date()
    fecha_fuera = hoy_madrid + timedelta(days=DIAS_MAX_RESERVA + 1)

    r = client.get(
        "/disponibilidad",
        params={"fecha": str(fecha_fuera), "servicio_id": servicio_corte.id},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    assert r.json()["horas_disponibles"] == []


def test_disponibilidad_fecha_lejana_vacio(client, cliente_token, servicio_corte):
    """Fecha = hoy+365 (muy lejana) → horas_disponibles vacías, sin error."""
    from datetime import datetime
    hoy_madrid = datetime.now(_MADRID).date()
    fecha_lejana = hoy_madrid + timedelta(days=365)

    r = client.get(
        "/disponibilidad",
        params={"fecha": str(fecha_lejana), "servicio_id": servicio_corte.id},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    assert r.json()["horas_disponibles"] == []
