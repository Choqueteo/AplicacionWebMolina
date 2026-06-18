from datetime import date, timedelta

_LUNES = {"dia_semana": 0, "hora_apertura": "09:00:00", "hora_cierre": "18:00:00"}


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_crear_horario_admin(client, admin_token):
    r = client.post("/horario", json=_LUNES, headers=_auth(admin_token))
    assert r.status_code == 201
    data = r.json()
    assert data["dia_semana"] == 0
    assert data["hora_apertura"] == "09:00:00"


def test_crear_horario_cliente_403(client, cliente_token):
    r = client.post("/horario", json=_LUNES, headers=_auth(cliente_token))
    assert r.status_code == 403


def test_listar_horario_autenticado(client, admin_token, cliente_token):
    client.post("/horario", json=_LUNES, headers=_auth(admin_token))
    r = client.get("/horario", headers=_auth(cliente_token))
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_tramo_solapado_rechazado(client, admin_token):
    client.post("/horario", json=_LUNES, headers=_auth(admin_token))
    # Tramo que se solapa (mismo horario) → 409
    r = client.post("/horario", json=_LUNES, headers=_auth(admin_token))
    assert r.status_code == 409


def test_multiples_tramos_mismo_dia(client, admin_token):
    manana = {"dia_semana": 0, "hora_apertura": "09:00:00", "hora_cierre": "14:00:00"}
    tarde  = {"dia_semana": 0, "hora_apertura": "17:00:00", "hora_cierre": "21:00:00"}
    r1 = client.post("/horario", json=manana, headers=_auth(admin_token))
    r2 = client.post("/horario", json=tarde,  headers=_auth(admin_token))
    assert r1.status_code == 201
    assert r2.status_code == 201
    # GET devuelve los 2 tramos del lunes
    r = client.get("/horario", headers=_auth(admin_token))
    lunes = [t for t in r.json() if t["dia_semana"] == 0]
    assert len(lunes) == 2


def test_tramo_solapado_parcial_rechazado(client, admin_token):
    manana = {"dia_semana": 0, "hora_apertura": "09:00:00", "hora_cierre": "14:00:00"}
    solape = {"dia_semana": 0, "hora_apertura": "13:00:00", "hora_cierre": "17:00:00"}
    client.post("/horario", json=manana, headers=_auth(admin_token))
    r = client.post("/horario", json=solape, headers=_auth(admin_token))
    assert r.status_code == 409


def test_disponibilidad_multiples_tramos(client, admin_token, cliente_token, db_session, servicio_corte):
    """Dos tramos no solapados en el mismo día: disponibilidad incluye slots de ambos bloques."""
    # Usar una fecha futura cuyo dia_semana sea lunes (0)
    hoy = date.today()
    dias_hasta_lunes = (0 - hoy.weekday()) % 7 or 7
    fecha_lunes = hoy + timedelta(days=dias_hasta_lunes)

    dia = fecha_lunes.weekday()
    manana = {"dia_semana": dia, "hora_apertura": "09:00:00", "hora_cierre": "12:00:00"}
    tarde  = {"dia_semana": dia, "hora_apertura": "16:00:00", "hora_cierre": "18:00:00"}
    client.post("/horario", json=manana, headers=_auth(admin_token))
    client.post("/horario", json=tarde,  headers=_auth(admin_token))

    r = client.get(
        "/disponibilidad",
        params={"fecha": str(fecha_lunes), "servicio_id": servicio_corte.id},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    horas = r.json()["horas_disponibles"]
    # Debe haber horas del tramo de mañana (ej. 09:00) y del tramo de tarde (ej. 16:00)
    assert any(h.startswith("09:") for h in horas), f"Falta tramo mañana: {horas}"
    assert any(h.startswith("16:") for h in horas), f"Falta tramo tarde: {horas}"
    # No debe haber horas del hueco del mediodía (12:30–15:30 no pertenece a ningún tramo)
    assert not any("12:30" <= h <= "15:30" for h in horas), f"Hueco contaminado: {horas}"


def test_actualizar_horario(client, admin_token):
    r = client.post("/horario", json=_LUNES, headers=_auth(admin_token))
    horario_id = r.json()["id"]

    r = client.put(
        f"/horario/{horario_id}",
        json={"hora_cierre": "20:00:00"},
        headers=_auth(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["hora_cierre"] == "20:00:00"
    assert r.json()["hora_apertura"] == "09:00:00"  # no cambió
