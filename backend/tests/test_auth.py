_PAYLOAD = {
    "email": "test@example.com",
    "password": "password123",
    "telefono": "612345678",
    "nombre_completo": "Test User",
}


def test_registro_exitoso(client):
    response = client.post("/registro", json=_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["rol"] == "cliente"
    assert "password" not in data
    assert "password_hash" not in data


def test_registro_rol_forzado_a_cliente(client):
    """Enviar rol=admin en el body debe ser rechazado (extra=forbid → 422)."""
    payload = {**_PAYLOAD, "email": "hacker@example.com", "rol": "admin"}
    response = client.post("/registro", json=payload)
    assert response.status_code == 422


def test_registro_email_duplicado(client):
    client.post("/registro", json=_PAYLOAD)
    response = client.post("/registro", json=_PAYLOAD)
    assert response.status_code == 409


def test_login_exitoso(client):
    client.post("/registro", json=_PAYLOAD)
    response = client.post("/login", json={
        "email": _PAYLOAD["email"],
        "password": _PAYLOAD["password"],
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_credenciales_incorrectas(client):
    response = client.post("/login", json={
        "email": "noexiste@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401
    detail = response.json()["detail"].lower()
    # El mensaje no debe revelar si el email existe o no
    assert "no existe" not in detail
    assert "email" not in detail


def test_endpoint_protegido_sin_token(client):
    response = client.get("/usuarios/me")
    assert response.status_code == 401


def test_endpoint_protegido_con_token(client):
    client.post("/registro", json=_PAYLOAD)
    login = client.post("/login", json={
        "email": _PAYLOAD["email"],
        "password": _PAYLOAD["password"],
    })
    token = login.json()["access_token"]

    response = client.get("/usuarios/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == _PAYLOAD["email"]
