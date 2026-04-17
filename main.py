"""
AgencyOS Telegram Bot entry point.
Calls backend FastAPI (localhost:8000) — no direct core/ or DB access.

Run: python main.py
Requires: TELEGRAM_BOT_TOKEN and AGENCYOS_API_KEY in .env
"""

import logging
import os

from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("agencyos.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

from bot.handlers import (
    handle_audit,
    handle_durum,
    handle_followup,
    handle_gonder,
    handle_lead,
    handle_liste,
    handle_mesaj,
    handle_teklif,
    handle_yardim,
)

COMMANDS = [
    ("lead",     handle_lead),
    ("liste",    handle_liste),
    ("audit",    handle_audit),
    ("mesaj",    handle_mesaj),
    ("gonder",   handle_gonder),
    ("followup", handle_followup),
    ("teklif",   handle_teklif),
    ("durum",    handle_durum),
    ("yardim",   handle_yardim),
    ("start",    handle_yardim),
    ("help",     handle_yardim),
]


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN .env'de tanimli degil")

    app = Application.builder().token(token).build()
    for cmd, handler in COMMANDS:
        app.add_handler(CommandHandler(cmd, handler))

    logger.info("AgencyOS bot basliyor... (API: %s)", os.getenv("AGENCYOS_API_URL", "http://localhost:8000"))
    app.run_polling()


if __name__ == "__main__":
    main()
