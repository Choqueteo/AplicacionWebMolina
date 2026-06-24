from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.constants import DIAS_MAX_RESERVA
from app.models import Cita, EstadoCita, FranjaOcupada, HorarioPeluquero, Rol, Usuario
from app.security import create_access_token, hash_password

_MADRID = ZoneInfo("Europe/Madrid")


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _payload(servicio_id, fecha, hora="10:00:00"):
    return {"servicio_id": servicio_id, "fecha": str(fecha), "hora_inicio": hora}


# ---------------------------------------------------------------------------
# Reserva exitosa
# ---------------------------------------------------------------------------

def test_reserva_exitosa(client, cliente_token, servicio_corte, horario_dia, fecha_test):
    """POST /citas con datos válidos → 201, hora_fin = hora_inicio + 30 min, estado activa."""
    r = client.post("/citas", json=_payload(servicio_corte.id, fecha_test), headers=_auth(cliente_token))
    assert r.status_code == 201
    data = r.json()
    assert data["hora_inicio"] == "10:00:00"
    assert data["hora_fin"] == "10:30:00"
    assert data["estado"] == "activa"
    assert data["servicio_id"] == servicio_corte.id


# ---------------------------------------------------------------------------
# Solapamiento → 409
# ---------------------------------------------------------------------------

def test_reserva_409_solapamiento(client, db_session, servicio_corte, horario_dia, fecha_test):
    """Segunda reserva al mismo slot → 409 Conflict (UNIQUE en FranjaOcupada)."""
    # Crear dos clientes distintos con tokens directos
    c1 = Usuario(email="c1@test.com", password_hash=hash_password("x"),
                 telefono="600000010", nombre_completo="C1", rol=Rol.cliente)
    c2 = Usuario(email="c2@test.com", password_hash=hash_password("x"),
                 telefono="600000011", nombre_completo="C2", rol=Rol.cliente)
    db_session.add_all([c1, c2])
    db_session.commit()
    db_session.refresh(c1)
    db_session.refresh(c2)

    token1 = create_access_token(c1.id, c1.rol.value)
    token2 = create_access_token(c2.id, c2.rol.value)

    payload = _payload(servicio_corte.id, fecha_test)
    r1 = client.post("/citas", json=payload, headers=_auth(token1))
    assert r1.status_code == 201

    r2 = client.post("/citas", json=payload, headers=_auth(token2))
    assert r2.status_code == 409


# ---------------------------------------------------------------------------
# Servicio de 60 min no cabe al final del horario → 422
# ---------------------------------------------------------------------------

def test_reserva_60min_no_cabe_al_final(client, cliente_token, servicio_tinte, horario_dia, fecha_test):
    """
    Tinte (60 min) a las 17:30 con cierre a las 18:00:
    17:30 + 60 min = 18:30 > 18:00 → fuera de horario → 422.
    """
    r = client.post(
        "/citas",
        json=_payload(servicio_tinte.id, fecha_test, hora="17:30:00"),
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Fecha pasada → 422
# ---------------------------------------------------------------------------

def test_reserva_fecha_pasada(client, cliente_token, servicio_corte, horario_dia):
    """Fecha en el pasado → 422."""
    fecha_pasada = date.today() - timedelta(days=1)
    r = client.post(
        "/citas",
        json=_payload(servicio_corte.id, fecha_pasada),
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Servicio inactivo → 422
# ---------------------------------------------------------------------------

def test_reserva_servicio_inactivo(client, cliente_token, db_session, horario_dia, fecha_test):
    """Reservar un servicio con activo=False → 422."""
    from decimal import Decimal
    from app.models import Servicio
    s = Servicio(nombre="Viejo", duracion_minutos=30, precio=Decimal("5.00"), activo=False)
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)

    r = client.post(
        "/citas",
        json=_payload(s.id, fecha_test),
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# cliente_id en el body → 422 (extra="forbid")
# ---------------------------------------------------------------------------

def test_reserva_cliente_id_en_body(client, cliente_token, servicio_corte, horario_dia, fecha_test):
    """Si el body incluye cliente_id, Pydantic lo rechaza con 422 (anti mass-assignment)."""
    payload = {
        "servicio_id": servicio_corte.id,
        "fecha": str(fecha_test),
        "hora_inicio": "10:00:00",
        "cliente_id": 9999,
    }
    r = client.post("/citas", json=payload, headers=_auth(cliente_token))
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /citas/mias — solo las del cliente autenticado
# ---------------------------------------------------------------------------

def test_citas_mias_solo_propias(client, db_session, servicio_corte, horario_dia, fecha_test):
    """GET /citas/mias devuelve únicamente las citas del cliente autenticado."""
    c1 = Usuario(email="c1@test.com", password_hash=hash_password("x"),
                 telefono="600000010", nombre_completo="C1", rol=Rol.cliente)
    c2 = Usuario(email="c2@test.com", password_hash=hash_password("x"),
                 telefono="600000011", nombre_completo="C2", rol=Rol.cliente)
    db_session.add_all([c1, c2])
    db_session.commit()
    db_session.refresh(c1)
    db_session.refresh(c2)

    token1 = create_access_token(c1.id, c1.rol.value)
    token2 = create_access_token(c2.id, c2.rol.value)

    # C1 reserva 10:00, C2 reserva 11:00
    client.post("/citas", json=_payload(servicio_corte.id, fecha_test, "10:00:00"), headers=_auth(token1))
    client.post("/citas", json=_payload(servicio_corte.id, fecha_test, "11:00:00"), headers=_auth(token2))

    r = client.get("/citas/mias", headers=_auth(token1))
    assert r.status_code == 200
    citas = r.json()
    assert len(citas) == 1
    assert citas[0]["cliente_id"] == c1.id
    assert citas[0]["hora_inicio"] == "10:00:00"


# ---------------------------------------------------------------------------
# GET /citas/{id} — anti-IDOR: otro cliente recibe 404
# ---------------------------------------------------------------------------

def test_obtener_cita_otro_cliente_404(client, db_session, servicio_corte, horario_dia, fecha_test):
    """GET /citas/{id} de la cita de otro cliente → 404 (no revela existencia)."""
    c1 = Usuario(email="c1@test.com", password_hash=hash_password("x"),
                 telefono="600000010", nombre_completo="C1", rol=Rol.cliente)
    c2 = Usuario(email="c2@test.com", password_hash=hash_password("x"),
                 telefono="600000011", nombre_completo="C2", rol=Rol.cliente)
    db_session.add_all([c1, c2])
    db_session.commit()
    db_session.refresh(c1)
    db_session.refresh(c2)

    token1 = create_access_token(c1.id, c1.rol.value)
    token2 = create_access_token(c2.id, c2.rol.value)

    r = client.post("/citas", json=_payload(servicio_corte.id, fecha_test), headers=_auth(token1))
    cita_id = r.json()["id"]

    # C2 intenta ver la cita de C1
    r2 = client.get(f"/citas/{cita_id}", headers=_auth(token2))
    assert r2.status_code == 404


# ---------------------------------------------------------------------------
# GET /citas — admin ve todas
# ---------------------------------------------------------------------------

def test_citas_admin_ve_todas(client, db_session, admin_token, servicio_corte, horario_dia, fecha_test):
    """GET /citas (admin) devuelve las citas de todos los clientes."""
    c1 = Usuario(email="c1@test.com", password_hash=hash_password("x"),
                 telefono="600000010", nombre_completo="C1", rol=Rol.cliente)
    c2 = Usuario(email="c2@test.com", password_hash=hash_password("x"),
                 telefono="600000011", nombre_completo="C2", rol=Rol.cliente)
    db_session.add_all([c1, c2])
    db_session.commit()
    db_session.refresh(c1)
    db_session.refresh(c2)

    t1 = create_access_token(c1.id, c1.rol.value)
    t2 = create_access_token(c2.id, c2.rol.value)

    client.post("/citas", json=_payload(servicio_corte.id, fecha_test, "10:00:00"), headers=_auth(t1))
    client.post("/citas", json=_payload(servicio_corte.id, fecha_test, "11:00:00"), headers=_auth(t2))

    r = client.get("/citas", headers=_auth(admin_token))
    assert r.status_code == 200
    assert len(r.json()) == 2


# ---------------------------------------------------------------------------
# Cancelación de citas
# ---------------------------------------------------------------------------

def test_cancelar_propia_cita(client, db_session, cliente_token, servicio_corte, horario_dia, fecha_test):
    """El dueño cancela su propia cita → 200, estado='cancelada', FranjaOcupada borradas."""
    r = client.post("/citas", json=_payload(servicio_corte.id, fecha_test), headers=_auth(cliente_token))
    assert r.status_code == 201
    cita_id = r.json()["id"]

    r = client.patch(f"/citas/{cita_id}/cancelar", headers=_auth(cliente_token))
    assert r.status_code == 200
    assert r.json()["estado"] == "cancelada"

    # Verificar que las franjas fueron borradas en BD
    franjas = db_session.query(FranjaOcupada).filter_by(cita_id=cita_id).all()
    assert franjas == []


def test_cancelar_otro_cliente_404(client, db_session, servicio_corte, horario_dia, fecha_test):
    """C2 intenta cancelar cita de C1 → 404 (anti-IDOR, no revela existencia)."""
    c1 = Usuario(email="c1@test.com", password_hash=hash_password("x"),
                 telefono="600000010", nombre_completo="C1", rol=Rol.cliente)
    c2 = Usuario(email="c2@test.com", password_hash=hash_password("x"),
                 telefono="600000011", nombre_completo="C2", rol=Rol.cliente)
    db_session.add_all([c1, c2])
    db_session.commit()
    db_session.refresh(c1)
    db_session.refresh(c2)

    t1 = create_access_token(c1.id, c1.rol.value)
    t2 = create_access_token(c2.id, c2.rol.value)

    r = client.post("/citas", json=_payload(servicio_corte.id, fecha_test), headers=_auth(t1))
    cita_id = r.json()["id"]

    r2 = client.patch(f"/citas/{cita_id}/cancelar", headers=_auth(t2))
    assert r2.status_code == 404


def test_admin_cancela_cualquier_cita(client, db_session, admin_token, servicio_corte, horario_dia, fecha_test):
    """Admin puede cancelar la cita de cualquier cliente → 200."""
    c = Usuario(email="c@test.com", password_hash=hash_password("x"),
                telefono="600000010", nombre_completo="C", rol=Rol.cliente)
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    token_c = create_access_token(c.id, c.rol.value)

    r = client.post("/citas", json=_payload(servicio_corte.id, fecha_test), headers=_auth(token_c))
    cita_id = r.json()["id"]

    r = client.patch(f"/citas/{cita_id}/cancelar", headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.json()["estado"] == "cancelada"


def test_cancelar_cita_pasada_422(client, db_session, cliente_token, servicio_corte):
    """Cita con fecha en el pasado insertada directamente en BD → PATCH devuelve 422."""
    from app.models import Servicio
    # Obtener el usuario del token (email cli@test.com creado por el fixture cliente_token)
    usuario = db_session.query(Usuario).filter_by(email="cli@test.com").first()

    cita_pasada = Cita(
        cliente_id=usuario.id,
        servicio_id=servicio_corte.id,
        fecha=date.today() - timedelta(days=1),
        hora_inicio=time(10, 0),
        hora_fin=time(10, 30),
        estado=EstadoCita.activa,
    )
    db_session.add(cita_pasada)
    db_session.commit()
    db_session.refresh(cita_pasada)

    r = client.patch(f"/citas/{cita_pasada.id}/cancelar", headers=_auth(cliente_token))
    assert r.status_code == 422


def test_cancelar_ya_cancelada_409(client, cliente_token, servicio_corte, horario_dia, fecha_test):
    """Cancelar una cita ya cancelada → segunda petición devuelve 409."""
    r = client.post("/citas", json=_payload(servicio_corte.id, fecha_test), headers=_auth(cliente_token))
    cita_id = r.json()["id"]

    r1 = client.patch(f"/citas/{cita_id}/cancelar", headers=_auth(cliente_token))
    assert r1.status_code == 200

    r2 = client.patch(f"/citas/{cita_id}/cancelar", headers=_auth(cliente_token))
    assert r2.status_code == 409


# ---------------------------------------------------------------------------
# No asistida
# ---------------------------------------------------------------------------

def test_no_asistida_admin_cita_pasada(client, db_session, admin_token, cliente_token, servicio_corte):
    """Admin marca una cita pasada activa como no_asistida → 200, estado='no_asistida'."""
    usuario = db_session.query(Usuario).filter_by(email="cli@test.com").first()
    cita_pasada = Cita(
        cliente_id=usuario.id,
        servicio_id=servicio_corte.id,
        fecha=date.today() - timedelta(days=1),
        hora_inicio=time(10, 0),
        hora_fin=time(10, 30),
        estado=EstadoCita.activa,
    )
    db_session.add(cita_pasada)
    db_session.commit()
    db_session.refresh(cita_pasada)

    r = client.patch(f"/citas/{cita_pasada.id}/no-asistida", headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.json()["estado"] == "no_asistida"


def test_no_asistida_cita_futura_422(client, admin_token, servicio_corte, horario_dia, fecha_test, cliente_token):
    """Admin intenta marcar como no_asistida una cita futura → 422."""
    r = client.post("/citas", json=_payload(servicio_corte.id, fecha_test), headers=_auth(cliente_token))
    assert r.status_code == 201
    cita_id = r.json()["id"]

    r = client.patch(f"/citas/{cita_id}/no-asistida", headers=_auth(admin_token))
    assert r.status_code == 422


def test_no_asistida_cita_cancelada_409(client, db_session, admin_token, cliente_token, servicio_corte):
    """Intentar marcar como no_asistida una cita cancelada → 409."""
    usuario = db_session.query(Usuario).filter_by(email="cli@test.com").first()
    cita = Cita(
        cliente_id=usuario.id,
        servicio_id=servicio_corte.id,
        fecha=date.today() - timedelta(days=1),
        hora_inicio=time(11, 0),
        hora_fin=time(11, 30),
        estado=EstadoCita.cancelada,
    )
    db_session.add(cita)
    db_session.commit()
    db_session.refresh(cita)

    r = client.patch(f"/citas/{cita.id}/no-asistida", headers=_auth(admin_token))
    assert r.status_code == 409


def test_no_asistida_cliente_403(client, db_session, cliente_token, servicio_corte):
    """Un cliente intenta marcar una cita como no_asistida → 403."""
    usuario = db_session.query(Usuario).filter_by(email="cli@test.com").first()
    cita = Cita(
        cliente_id=usuario.id,
        servicio_id=servicio_corte.id,
        fecha=date.today() - timedelta(days=1),
        hora_inicio=time(12, 0),
        hora_fin=time(12, 30),
        estado=EstadoCita.activa,
    )
    db_session.add(cita)
    db_session.commit()
    db_session.refresh(cita)

    r = client.patch(f"/citas/{cita.id}/no-asistida", headers=_auth(cliente_token))
    assert r.status_code == 403


def test_no_asistida_incrementa_contador(client, db_session, admin_token, cliente_token, servicio_corte):
    """Marcar una cita como no_asistida incrementa usuario.inasistencias en 1."""
    usuario = db_session.query(Usuario).filter_by(email="cli@test.com").first()
    cita = Cita(
        cliente_id=usuario.id,
        servicio_id=servicio_corte.id,
        fecha=date.today() - timedelta(days=1),
        hora_inicio=time(14, 0),
        hora_fin=time(14, 30),
        estado=EstadoCita.activa,
    )
    db_session.add(cita)
    db_session.commit()
    db_session.refresh(cita)

    r = client.patch(f"/citas/{cita.id}/no-asistida", headers=_auth(admin_token))
    assert r.status_code == 200

    r = client.get(f"/usuarios/{usuario.id}", headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.json()["inasistencias"] == 1


def test_listar_citas_filtro_fecha(client, db_session, admin_token, servicio_corte, horario_dia, fecha_test):
    """GET /citas?fecha=X devuelve solo las citas de esa fecha."""
    c1 = Usuario(email="c1@test.com", password_hash=hash_password("x"),
                 telefono="600000010", nombre_completo="C1", rol=Rol.cliente)
    c2 = Usuario(email="c2@test.com", password_hash=hash_password("x"),
                 telefono="600000011", nombre_completo="C2", rol=Rol.cliente)
    db_session.add_all([c1, c2])
    db_session.commit()
    db_session.refresh(c1)
    db_session.refresh(c2)

    t1 = create_access_token(c1.id, c1.rol.value)
    t2 = create_access_token(c2.id, c2.rol.value)

    otra_fecha = fecha_test + timedelta(days=1)

    # Reserva en fecha_test
    client.post("/citas", json=_payload(servicio_corte.id, fecha_test, "10:00:00"), headers=_auth(t1))
    # Reserva en otra_fecha (no debe aparecer en el filtro)
    client.post("/citas", json=_payload(servicio_corte.id, otra_fecha, "10:00:00"), headers=_auth(t2))

    r = client.get(f"/citas?fecha={fecha_test}", headers=_auth(admin_token))
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["fecha"] == str(fecha_test)


def test_cancelar_libera_franja_para_nueva_reserva(client, db_session, servicio_corte, horario_dia, fecha_test):
    """Tras cancelar, el slot queda libre y otro cliente puede reservarlo → 201."""
    c1 = Usuario(email="c1@test.com", password_hash=hash_password("x"),
                 telefono="600000010", nombre_completo="C1", rol=Rol.cliente)
    c2 = Usuario(email="c2@test.com", password_hash=hash_password("x"),
                 telefono="600000011", nombre_completo="C2", rol=Rol.cliente)
    db_session.add_all([c1, c2])
    db_session.commit()
    db_session.refresh(c1)
    db_session.refresh(c2)

    t1 = create_access_token(c1.id, c1.rol.value)
    t2 = create_access_token(c2.id, c2.rol.value)

    # C1 reserva 10:00
    r = client.post("/citas", json=_payload(servicio_corte.id, fecha_test, "10:00:00"), headers=_auth(t1))
    assert r.status_code == 201
    cita_id = r.json()["id"]

    # C1 cancela
    r = client.patch(f"/citas/{cita_id}/cancelar", headers=_auth(t1))
    assert r.status_code == 200

    # C2 reserva el mismo slot — debe funcionar (franja liberada)
    r = client.post("/citas", json=_payload(servicio_corte.id, fecha_test, "10:00:00"), headers=_auth(t2))
    assert r.status_code == 201


# ---------------------------------------------------------------------------
# Servicio de 300 min y validación hora :15
# ---------------------------------------------------------------------------

def test_reserva_300min_exitosa(client, cliente_token, db_session, horario_dia, fecha_test):
    """Servicio 300 min (5 h = 10 franjas): hora_fin 14:00, crea 10 FranjaOcupada (09:00–13:30 en :00/:30)."""
    from decimal import Decimal
    from app.models import Servicio
    s = Servicio(nombre="Servicio largo", duracion_minutos=300, precio=Decimal("50.00"), activo=True)
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)

    r = client.post("/citas", json=_payload(s.id, fecha_test, hora="09:00:00"), headers=_auth(cliente_token))
    assert r.status_code == 201
    data = r.json()
    assert data["hora_inicio"] == "09:00:00"
    assert data["hora_fin"] == "14:00:00"

    franjas = sorted(
        db_session.query(FranjaOcupada).filter_by(cita_id=data["id"]).all(),
        key=lambda f: f.hora,
    )
    assert len(franjas) == 10
    assert franjas[0].hora == time(9, 0)
    assert franjas[9].hora == time(13, 30)


def test_hora_inicio_15_invalido(client, cliente_token, servicio_corte, horario_dia, fecha_test):
    """hora_inicio en :15 es inválido con franjas de 30 min → 422."""
    r = client.post(
        "/citas",
        json=_payload(servicio_corte.id, fecha_test, hora="10:15:00"),
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Múltiples tramos de horario en el mismo día
# ---------------------------------------------------------------------------

def test_reserva_segundo_tramo_del_dia(client, cliente_token, db_session, servicio_corte, fecha_test):
    """
    Día con tramos 09:00-14:00 y 17:00-22:00.
    Reservar a las 17:00 (segundo tramo) → 201.
    """
    db_session.add(HorarioPeluquero(dia_semana=fecha_test.weekday(), hora_apertura=time(9, 0),  hora_cierre=time(14, 0)))
    db_session.add(HorarioPeluquero(dia_semana=fecha_test.weekday(), hora_apertura=time(17, 0), hora_cierre=time(22, 0)))
    db_session.commit()

    r = client.post("/citas", json=_payload(servicio_corte.id, fecha_test, "17:00:00"), headers=_auth(cliente_token))
    assert r.status_code == 201
    assert r.json()["hora_inicio"] == "17:00:00"
    assert r.json()["hora_fin"]    == "17:30:00"


def test_reserva_entre_tramos_422(client, cliente_token, db_session, servicio_corte, fecha_test):
    """
    Día con tramos 09:00-14:00 y 17:00-22:00.
    Reservar a las 15:00 (hueco entre tramos) → 422.
    """
    db_session.add(HorarioPeluquero(dia_semana=fecha_test.weekday(), hora_apertura=time(9, 0),  hora_cierre=time(14, 0)))
    db_session.add(HorarioPeluquero(dia_semana=fecha_test.weekday(), hora_apertura=time(17, 0), hora_cierre=time(22, 0)))
    db_session.commit()

    r = client.post("/citas", json=_payload(servicio_corte.id, fecha_test, "15:00:00"), headers=_auth(cliente_token))
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Ventana de reserva [hoy, hoy+DIAS_MAX_RESERVA]
# ---------------------------------------------------------------------------

def test_reserva_limite_30_ok(client, cliente_token, servicio_corte, db_session):
    """Fecha = hoy+30 (límite inclusive) con horario → 201."""
    hoy_madrid = datetime.now(_MADRID).date()
    fecha_limite = hoy_madrid + timedelta(days=DIAS_MAX_RESERVA)

    h = HorarioPeluquero(
        dia_semana=fecha_limite.weekday(),
        hora_apertura=time(9, 0),
        hora_cierre=time(18, 0),
    )
    db_session.add(h)
    db_session.commit()

    r = client.post(
        "/citas",
        json=_payload(servicio_corte.id, fecha_limite),
        headers=_auth(cliente_token),
    )
    assert r.status_code == 201


def test_reserva_limite_31_422(client, cliente_token, servicio_corte):
    """Fecha = hoy+31 (fuera de ventana) → 422 con mensaje sobre antelación."""
    hoy_madrid = datetime.now(_MADRID).date()
    fecha_fuera = hoy_madrid + timedelta(days=DIAS_MAX_RESERVA + 1)

    r = client.post(
        "/citas",
        json=_payload(servicio_corte.id, fecha_fuera),
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422
    assert "antelación" in r.json()["detail"]


def test_reserva_fecha_lejana_422(client, cliente_token, servicio_corte):
    """Fecha = hoy+365 (muy lejana) → 422."""
    hoy_madrid = datetime.now(_MADRID).date()
    fecha_lejana = hoy_madrid + timedelta(days=365)

    r = client.post(
        "/citas",
        json=_payload(servicio_corte.id, fecha_lejana),
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422
