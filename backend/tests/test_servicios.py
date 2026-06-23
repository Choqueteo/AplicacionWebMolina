_PAYLOAD = {"nombre": "Corte", "duracion_minutos": 30, "precio": "15.00"}


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_crear_servicio_admin(client, admin_token):
    r = client.post("/servicios", json=_PAYLOAD, headers=_auth(admin_token))
    assert r.status_code == 201
    data = r.json()
    assert data["nombre"] == "Corte"
    assert data["activo"] is True


def test_crear_servicio_cliente_403(client, cliente_token):
    r = client.post("/servicios", json=_PAYLOAD, headers=_auth(cliente_token))
    assert r.status_code == 403


def test_duracion_no_multiplo_30(client, admin_token):
    payload = {**_PAYLOAD, "duracion_minutos": 45}
    r = client.post("/servicios", json=payload, headers=_auth(admin_token))
    assert r.status_code == 422


def test_servicio_300min_valido(client, admin_token):
    payload = {**_PAYLOAD, "nombre": "Servicio largo", "duracion_minutos": 300}
    r = client.post("/servicios", json=payload, headers=_auth(admin_token))
    assert r.status_code == 201
    assert r.json()["duracion_minutos"] == 300


def test_servicio_330min_invalido(client, admin_token):
    """330 min excede el máximo de 300."""
    payload = {**_PAYLOAD, "nombre": "Excedido", "duracion_minutos": 330}
    r = client.post("/servicios", json=payload, headers=_auth(admin_token))
    assert r.status_code == 422


def test_servicio_360min_invalido(client, admin_token):
    """360 min es múltiplo de 30 pero excede el máximo de 300."""
    payload = {**_PAYLOAD, "nombre": "Excedido", "duracion_minutos": 360}
    r = client.post("/servicios", json=payload, headers=_auth(admin_token))
    assert r.status_code == 422


def test_listar_solo_activos(client, admin_token, cliente_token):
    # Crear servicio y luego borrarlo lógicamente
    r = client.post("/servicios", json=_PAYLOAD, headers=_auth(admin_token))
    servicio_id = r.json()["id"]
    client.delete(f"/servicios/{servicio_id}", headers=_auth(admin_token))

    # El cliente no debe verlo en la lista
    r = client.get("/servicios", headers=_auth(cliente_token))
    assert r.status_code == 200
    ids = [s["id"] for s in r.json()]
    assert servicio_id not in ids


def test_admin_ve_inactivos(client, admin_token):
    r = client.post("/servicios", json=_PAYLOAD, headers=_auth(admin_token))
    servicio_id = r.json()["id"]
    client.delete(f"/servicios/{servicio_id}", headers=_auth(admin_token))

    r = client.get("/servicios?incluir_inactivos=true", headers=_auth(admin_token))
    assert r.status_code == 200
    ids = [s["id"] for s in r.json()]
    assert servicio_id in ids


def test_actualizar_servicio(client, admin_token):
    r = client.post("/servicios", json=_PAYLOAD, headers=_auth(admin_token))
    servicio_id = r.json()["id"]

    r = client.put(
        f"/servicios/{servicio_id}",
        json={"nombre": "Corte Premium", "precio": "20.00"},
        headers=_auth(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["nombre"] == "Corte Premium"
    assert r.json()["duracion_minutos"] == 30  # no cambió


def test_borrar_logico(client, admin_token):
    r = client.post("/servicios", json=_PAYLOAD, headers=_auth(admin_token))
    servicio_id = r.json()["id"]

    r = client.delete(f"/servicios/{servicio_id}", headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.json()["activo"] is False

    # El servicio sigue en BD — visible para admin con incluir_inactivos
    r = client.get(f"/servicios/{servicio_id}", headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.json()["activo"] is False


def test_reactivar_servicio_via_put(client, admin_token):
    """DELETE desactiva; PUT con {activo: true} reactiva el servicio."""
    r = client.post("/servicios", json=_PAYLOAD, headers=_auth(admin_token))
    servicio_id = r.json()["id"]

    client.delete(f"/servicios/{servicio_id}", headers=_auth(admin_token))

    r = client.put(
        f"/servicios/{servicio_id}",
        json={"activo": True},
        headers=_auth(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["activo"] is True
