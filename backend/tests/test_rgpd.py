"""
Tests RGPD: exportación (portabilidad) y supresión (anonimización) de datos.
"""
from datetime import date, time, timedelta

import pytest
from app.models import Cita, EstadoCita, FranjaOcupada, Rol, Usuario
from app.security import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Fixtures locales
# ---------------------------------------------------------------------------

@pytest.fixture()
def usuario_rgpd(db_session):
    """Cliente con credenciales conocidas para pruebas RGPD."""
    u = Usuario(
        email="rgpd@test.com",
        password_hash=hash_password("pass12345678"),
        telefono="611111111",
        nombre_completo="Usuario RGPD",
        rol=Rol.cliente,
        consentimiento_version="v1",
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture()
def token_rgpd(usuario_rgpd):
    return create_access_token(usuario_rgpd.id, usuario_rgpd.rol.value)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _cita_futura(db_session, usuario, servicio, dias=2):
    fecha = date.today() + timedelta(days=dias)
    cita = Cita(
        cliente_id=usuario.id,
        servicio_id=servicio.id,
        fecha=fecha,
        hora_inicio=time(10, 0),
        hora_fin=time(10, 30),
        estado=EstadoCita.activa,
    )
    db_session.add(cita)
    db_session.flush()
    franja = FranjaOcupada(cita_id=cita.id, fecha=fecha, hora=time(10, 0))
    db_session.add(franja)
    db_session.commit()
    return cita


def _cita_pasada(db_session, usuario, servicio, dias=5):
    fecha = date.today() - timedelta(days=dias)
    cita = Cita(
        cliente_id=usuario.id,
        servicio_id=servicio.id,
        fecha=fecha,
        hora_inicio=time(10, 0),
        hora_fin=time(10, 30),
        estado=EstadoCita.activa,
    )
    db_session.add(cita)
    db_session.commit()
    return cita


# ---------------------------------------------------------------------------
# Tests: exportar datos (GET /usuarios/me/datos)
# ---------------------------------------------------------------------------

def test_exportar_devuelve_perfil_y_citas(client, db_session, usuario_rgpd, token_rgpd, servicio_corte):
    _cita_futura(db_session, usuario_rgpd, servicio_corte)

    r = client.get("/usuarios/me/datos", headers=_auth(token_rgpd))

    assert r.status_code == 200
    data = r.json()
    assert data["perfil"]["email"] == "rgpd@test.com"
    assert len(data["citas"]) == 1
    assert data["citas"][0]["servicio_nombre"] == "Corte"


def test_exportar_no_incluye_citas_ajenas(client, db_session, usuario_rgpd, token_rgpd, servicio_corte):
    otro = Usuario(
        email="otro@test.com",
        password_hash=hash_password("pass12345678"),
        telefono="622222222",
        nombre_completo="Otro Usuario",
        rol=Rol.cliente,
    )
    db_session.add(otro)
    db_session.flush()
    _cita_futura(db_session, otro, servicio_corte)

    r = client.get("/usuarios/me/datos", headers=_auth(token_rgpd))

    assert r.status_code == 200
    assert len(r.json()["citas"]) == 0


def test_exportar_sin_token_401(client):
    r = client.get("/usuarios/me/datos")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Tests: eliminar cuenta (DELETE /usuarios/me)
# ---------------------------------------------------------------------------

def test_eliminar_sin_token_401(client):
    r = client.delete("/usuarios/me")
    assert r.status_code == 401


def test_anonimizar_sustituye_campos(client, db_session, usuario_rgpd, token_rgpd):
    r = client.delete("/usuarios/me", headers=_auth(token_rgpd))

    assert r.status_code == 200
    db_session.refresh(usuario_rgpd)
    assert usuario_rgpd.email.startswith("anon_")
    assert usuario_rgpd.nombre_completo == "Usuario eliminado"
    assert usuario_rgpd.telefono == "000000000"
    assert usuario_rgpd.password_hash == "ANONIMIZADO"


def test_anonimizar_impide_login_posterior(client, db_session, usuario_rgpd, token_rgpd):
    client.delete("/usuarios/me", headers=_auth(token_rgpd))

    r = client.post("/login", json={"email": "rgpd@test.com", "password": "pass12345678"})

    assert r.status_code == 401


def test_anonimizar_cancela_citas_futuras_libera_franjas(
    client, db_session, usuario_rgpd, token_rgpd, servicio_corte
):
    cita = _cita_futura(db_session, usuario_rgpd, servicio_corte)
    cita_id = cita.id

    r = client.delete("/usuarios/me", headers=_auth(token_rgpd))

    assert r.status_code == 200
    db_session.expire_all()
    cita_db = db_session.get(Cita, cita_id)
    assert cita_db.estado == EstadoCita.cancelada
    franjas = db_session.query(FranjaOcupada).filter(FranjaOcupada.cita_id == cita_id).all()
    assert len(franjas) == 0


def test_anonimizar_conserva_citas_pasadas(
    client, db_session, usuario_rgpd, token_rgpd, servicio_corte
):
    cita = _cita_pasada(db_session, usuario_rgpd, servicio_corte)
    cita_id = cita.id

    r = client.delete("/usuarios/me", headers=_auth(token_rgpd))

    assert r.status_code == 200
    db_session.expire_all()
    cita_db = db_session.get(Cita, cita_id)
    assert cita_db is not None
    assert cita_db.estado == EstadoCita.activa


def test_admin_no_puede_autoborrarse(client, admin_token):
    r = client.delete("/usuarios/me", headers=_auth(admin_token))
    assert r.status_code == 403


def test_anonimizar_idempotente(client, token_rgpd):
    r1 = client.delete("/usuarios/me", headers=_auth(token_rgpd))
    assert r1.status_code == 200
    r2 = client.delete("/usuarios/me", headers=_auth(token_rgpd))
    assert r2.status_code == 200
