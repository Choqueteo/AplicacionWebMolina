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


def test_dia_duplicado(client, admin_token):
    client.post("/horario", json=_LUNES, headers=_auth(admin_token))
    # Segundo intento con el mismo día → 409
    r = client.post("/horario", json=_LUNES, headers=_auth(admin_token))
    assert r.status_code == 409


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
