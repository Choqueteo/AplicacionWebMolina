import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def enviar_aviso_peluquero(mensaje: str) -> None:
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id
    if not token or not chat_id:
        logger.warning(
            "Telegram no configurado (TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID ausentes) — aviso omitido."
        )
        return
    try:
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": mensaje},
            timeout=5,
        )
    except Exception:
        logger.warning("Fallo al enviar aviso Telegram — la operación principal no se ve afectada.")
