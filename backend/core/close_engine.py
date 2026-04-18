"""
Close Engine — generates a short, low-friction meeting-booking message.
"""

import logging

from core.utils import claude_api_call
from core.prompts import build_close_prompt

logger = logging.getLogger(__name__)

_FALLBACK = "Bunu size 10 dakikada gösterebilirim — yarın mı daha uygun olur, yoksa haftaya mı?"


async def generate_close_message(lead: dict) -> str:
    """Returns a 1-2 sentence close message aimed at booking a meeting."""
    prompt = build_close_prompt(lead)
    result = await claude_api_call(prompt, max_tokens=120, temperature=0.3)
    text = (result or "").strip()
    logger.info("Close mesaji uretildi: lead=%s", lead.get("isim"))
    return text or _FALLBACK
