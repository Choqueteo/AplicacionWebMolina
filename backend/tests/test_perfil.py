"""Tests para PATCH /usuarios/me y PATCH /usuarios/me/password."""


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── PATCH /usuarios/me ────────────────────────────────────────────────────────

def test_actualizar_nombre_exitoso(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={"nombre_completo": "Juan Pedro García"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    assert r.json()["nombre_completo"] == "Juan Pedro García"


def test_actualizar_telefono_exitoso(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={"telefono": "698765432"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    assert r.json()["telefono"] == "698765432"


def test_actualizar_ambos_campos(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={"nombre_completo": "Ana María López", "telefono": "711222333"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["nombre_completo"] == "Ana María López"
    assert data["telefono"] == "711222333"


def test_actualizar_nombre_normaliza_espacios(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={"nombre_completo": "  Juan   Pérez  "},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    assert r.json()["nombre_completo"] == "Juan Pérez"


def test_actualizar_nombre_una_sola_palabra_422(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={"nombre_completo": "Solo"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


def test_actualizar_telefono_invalido_422(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={"telefono": "512345678"},  # empieza por 5 — no válido en España
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


def test_actualizar_sin_campos_422(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


def test_actualizar_campo_email_rechazado(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={"email": "otro@example.com"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


def test_actualizar_campo_rol_rechazado(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={"rol": "admin"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


def test_actualizar_campo_bloqueado_rechazado(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={"bloqueado": False, "nombre_completo": "Juan Pedro García"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


def test_actualizar_perfil_sin_token_401(client):
    r = client.patch(
        "/usuarios/me",
        json={"nombre_completo": "Juan Pedro García"},
    )
    assert r.status_code == 401


# ── PATCH /usuarios/me/password ───────────────────────────────────────────────

def test_cambiar_password_exitoso(client, cliente_token):
    r = client.patch(
        "/usuarios/me/password",
        json={"password_actual": "clientepass123", "password_nueva": "nuevaClave99"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200


def test_cambiar_password_actual_incorrecta_400(client, cliente_token):
    r = client.patch(
        "/usuarios/me/password",
        json={"password_actual": "contraseñaErronea", "password_nueva": "nuevaClave99"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 400
    assert "contraseña actual" in r.json()["detail"].lower()


def test_cambiar_password_nueva_demasiado_corta_422(client, cliente_token):
    r = client.patch(
        "/usuarios/me/password",
        json={"password_actual": "clientepass123", "password_nueva": "corta"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


def test_cambiar_password_campo_extra_rechazado(client, cliente_token):
    r = client.patch(
        "/usuarios/me/password",
        json={
            "password_actual": "clientepass123",
            "password_nueva": "nuevaClave99",
            "email": "hacker@x.com",
        },
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


def test_cambiar_password_sin_token_401(client):
    r = client.patch(
        "/usuarios/me/password",
        json={"password_actual": "clientepass123", "password_nueva": "nuevaClave99"},
    )
    assert r.status_code == 401
