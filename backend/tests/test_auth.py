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


# ---------------------------------------------------------------------------
# Validación de nombre_completo
# ---------------------------------------------------------------------------

def test_nombre_valido_tildes(client):
    """Tildes y guión compuesto son válidos → 201."""
    r = client.post("/registro", json={**_PAYLOAD, "email": "n1@x.com",
                                       "nombre_completo": "María José García-López"})
    assert r.status_code == 201


def test_nombre_valido_apostrofo(client):
    """Apóstrofo en apellido es válido → 201."""
    r = client.post("/registro", json={**_PAYLOAD, "email": "n2@x.com",
                                       "nombre_completo": "Cristian O'Brien López"})
    assert r.status_code == 201


def test_nombre_normaliza_espacios(client):
    """Espacios extra se normalizan; el valor guardado está limpio."""
    r = client.post("/registro", json={**_PAYLOAD, "email": "n3@x.com",
                                       "nombre_completo": "  Juan   Pérez  "})
    assert r.status_code == 201
    assert r.json()["nombre_completo"] == "Juan Pérez"


def test_nombre_una_sola_palabra_422(client):
    """Una sola palabra → 422."""
    r = client.post("/registro", json={**_PAYLOAD, "email": "n4@x.com",
                                       "nombre_completo": "Juan"})
    assert r.status_code == 422


def test_nombre_con_digito_422(client):
    """Dígito en el nombre → 422."""
    r = client.post("/registro", json={**_PAYLOAD, "email": "n5@x.com",
                                       "nombre_completo": "Juan P3rez"})
    assert r.status_code == 422


def test_nombre_vacio_422(client):
    """Cadena vacía → 422."""
    r = client.post("/registro", json={**_PAYLOAD, "email": "n6@x.com",
                                       "nombre_completo": ""})
    assert r.status_code == 422


def test_nombre_solo_espacios_422(client):
    """Solo espacios → vacío tras normalizar → 422."""
    r = client.post("/registro", json={**_PAYLOAD, "email": "n7@x.com",
                                       "nombre_completo": "   "})
    assert r.status_code == 422


def test_nombre_simbolo_arroba_422(client):
    """Símbolo @ en el nombre → 422."""
    r = client.post("/registro", json={**_PAYLOAD, "email": "n8@x.com",
                                       "nombre_completo": "Juan @Pérez"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Validación de telefono
# ---------------------------------------------------------------------------

def test_telefono_con_prefijo_34(client):
    """Prefijo +34 con espacios → aceptado; guardado como 9 dígitos."""
    r = client.post("/registro", json={**_PAYLOAD, "email": "t1@x.com",
                                       "telefono": "+34 612 34 56 78"})
    assert r.status_code == 201
    assert r.json()["telefono"] == "612345678"


def test_telefono_con_guiones(client):
    """Guiones como separadores → aceptado; guardado como 9 dígitos."""
    r = client.post("/registro", json={**_PAYLOAD, "email": "t2@x.com",
                                       "telefono": "612-345-678"})
    assert r.status_code == 201
    assert r.json()["telefono"] == "612345678"


def test_telefono_prefijo_0034(client):
    """Prefijo 0034 → aceptado; guardado como 9 dígitos."""
    r = client.post("/registro", json={**_PAYLOAD, "email": "t3@x.com",
                                       "telefono": "0034612345678"})
    assert r.status_code == 201
    assert r.json()["telefono"] == "612345678"


def test_telefono_con_letras_422(client):
    """Letras en el teléfono → 422."""
    r = client.post("/registro", json={**_PAYLOAD, "email": "t4@x.com",
                                       "telefono": "ABC345678"})
    assert r.status_code == 422


def test_telefono_demasiado_corto_422(client):
    """Menos de 9 dígitos significativos → 422."""
    r = client.post("/registro", json={**_PAYLOAD, "email": "t5@x.com",
                                       "telefono": "61234"})
    assert r.status_code == 422


def test_telefono_primer_digito_invalido_422(client):
    """Primer dígito fuera del rango 6-9 (p. ej. 5) → 422."""
    r = client.post("/registro", json={**_PAYLOAD, "email": "t6@x.com",
                                       "telefono": "512345678"})
    assert r.status_code == 422
