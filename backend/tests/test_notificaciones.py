"""Tests para las notificaciones Telegram al peluquero."""
from unittest.mock import patch

import httpx
import pytest


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── Bloque A: tests de endpoint ───────────────────────────────────────────────
# Mockean enviar_aviso_peluquero en el punto donde está importado en citas.py

def test_reserva_dispara_aviso(client, cliente_token, servicio_corte, horario_dia, fecha_test):
    with patch("app.routers.citas.enviar_aviso_peluquero") as mock_fn:
        r = client.post(
            "/citas",
            json={
                "servicio_id": servicio_corte.id,
                "fecha": str(fecha_test),
                "hora_inicio": "10:00:00",
            },
            headers=_auth(cliente_token),
        )
    assert r.status_code == 201
    mock_fn.assert_called_once()


def test_reserva_mensaje_contiene_datos(client, cliente_token, servicio_corte, horario_dia, fecha_test):
    with patch("app.routers.citas.enviar_aviso_peluquero") as mock_fn:
        r = client.post(
            "/citas",
            json={
                "servicio_id": servicio_corte.id,
                "fecha": str(fecha_test),
                "hora_inicio": "10:00:00",
            },
            headers=_auth(cliente_token),
        )
    assert r.status_code == 201
    mensaje = mock_fn.call_args[0][0]
    assert "Cliente Test" in mensaje          # nombre del fixture cliente_token
    assert "600000001" in mensaje             # teléfono del fixture
    assert "Corte" in mensaje                 # nombre del servicio fixture
    assert fecha_test.strftime("%d/%m/%Y") in mensaje
    assert "10:00" in mensaje


def test_cancelacion_cliente_dispara_aviso(client, cliente_token, servicio_corte, horario_dia, fecha_test):
    r = client.post(
        "/citas",
        json={
            "servicio_id": servicio_corte.id,
            "fecha": str(fecha_test),
            "hora_inicio": "10:00:00",
        },
        headers=_auth(cliente_token),
    )
    assert r.status_code == 201
    cita_id = r.json()["id"]

    with patch("app.routers.citas.enviar_aviso_peluquero") as mock_fn:
        r2 = client.patch(f"/citas/{cita_id}/cancelar", headers=_auth(cliente_token))
    assert r2.status_code == 200
    mock_fn.assert_called_once()


def test_cancelacion_admin_no_dispara_aviso(
    client, cliente_token, admin_token, servicio_corte, horario_dia, fecha_test
):
    r = client.post(
        "/citas",
        json={
            "servicio_id": servicio_corte.id,
            "fecha": str(fecha_test),
            "hora_inicio": "10:00:00",
        },
        headers=_auth(cliente_token),
    )
    assert r.status_code == 201
    cita_id = r.json()["id"]

    with patch("app.routers.citas.enviar_aviso_peluquero") as mock_fn:
        r2 = client.patch(f"/citas/{cita_id}/cancelar", headers=_auth(admin_token))
    assert r2.status_code == 200
    mock_fn.assert_not_called()


# ── Bloque B: tests unitarios del módulo telegram ─────────────────────────────
# Mockean httpx.post directamente dentro del módulo

def test_sin_token_telegram_httpx_no_se_llama():
    from app.notificaciones.telegram import enviar_aviso_peluquero

    with (
        patch("app.notificaciones.telegram.settings") as mock_cfg,
        patch("app.notificaciones.telegram.httpx.post") as mock_post,
    ):
        mock_cfg.telegram_bot_token = None
        mock_cfg.telegram_chat_id = None
        enviar_aviso_peluquero("hola")
    mock_post.assert_not_called()


def test_excepcion_httpx_no_propaga():
    from app.notificaciones.telegram import enviar_aviso_peluquero

    with (
        patch("app.notificaciones.telegram.settings") as mock_cfg,
        patch("app.notificaciones.telegram.httpx.post") as mock_post,
    ):
        mock_cfg.telegram_bot_token = "tok"
        mock_cfg.telegram_chat_id = "999"
        mock_post.side_effect = httpx.NetworkError("caído")
        enviar_aviso_peluquero("hola")  # no debe lanzar


def test_reserva_falla_envio_devuelve_201(
    client, cliente_token, servicio_corte, horario_dia, fecha_test
):
    with patch(
        "app.routers.citas.enviar_aviso_peluquero",
        side_effect=Exception("Telegram caído"),
    ):
        r = client.post(
            "/citas",
            json={
                "servicio_id": servicio_corte.id,
                "fecha": str(fecha_test),
                "hora_inicio": "10:00:00",
            },
            headers=_auth(cliente_token),
        )
    assert r.status_code == 201
