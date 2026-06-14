from datetime import date, time, timedelta

from app.models import FranjaOcupada


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_disponibilidad_dia_con_horario(client, cliente_token, servicio_corte, horario_dia, fecha_test):
    """Día con horario 09:00-18:00 y servicio de 30 min → devuelve slots de 09:00 a 17:30."""
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
    assert "17:30:00" in horas
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
