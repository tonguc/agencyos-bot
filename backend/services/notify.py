"""Admin notification — Telegram bot API ile fire-and-forget mesaj gonderir.

Kullanim: kritik prod event'lerinde (Apify 402, Claude rate limit storm, vb.)
bekletmeden alarm. Konfigurasyon yoksa (TELEGRAM_BOT_TOKEN bos) sessiz log.
"""

import asyncio
import logging
import time

import requests

from config import settings

logger = logging.getLogger(__name__)

# Aynı mesaj için tekrar tekrar bildirim atmamak için kısa-süre debounce.
# {hash(text): epoch_seconds_last_sent}
_LAST_SENT: dict[int, float] = {}
_DEBOUNCE_SECONDS = 600  # 10 dk: aynı uyarı tekrar düşerse 10 dk içinde 1 kez yollanır


def _admin_chat_ids() -> list[str]:
    raw = settings.ADMIN_TELEGRAM_CHAT_IDS or ""
    return [c.strip() for c in raw.split(",") if c.strip()]


async def notify_admin(text: str) -> None:
    """Async fire-and-forget — caller'i bloklamaz, exception sızdırmaz."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.info("notify_admin: TELEGRAM_BOT_TOKEN bos, atlandi | text=%r", text[:120])
        return
    chat_ids = _admin_chat_ids()
    if not chat_ids:
        logger.info("notify_admin: ADMIN_TELEGRAM_CHAT_IDS bos, atlandi | text=%r", text[:120])
        return

    key = hash(text)
    now = time.time()
    last = _LAST_SENT.get(key, 0)
    if now - last < _DEBOUNCE_SECONDS:
        logger.debug("notify_admin: debounced (%.0fs sonra) | text=%r",
                     _DEBOUNCE_SECONDS - (now - last), text[:80])
        return
    _LAST_SENT[key] = now

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in chat_ids:
        try:
            await asyncio.to_thread(
                requests.post,
                url,
                json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
                timeout=10,
            )
            logger.info("notify_admin: gonderildi | chat=%s text=%r", chat_id, text[:80])
        except Exception as e:
            # Notify path operasyonel flow'u kirmamali — sadece log.
            logger.warning("notify_admin failed | chat=%s err=%s", chat_id, e)
