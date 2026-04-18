"""
Response Engine — generates contextual reply to a classified lead message.
Templates for low-stakes intents; Claude for intents that need personalization.
"""

import logging

from core.utils import claude_api_call
from core.prompts import build_reply_response_prompt

logger = logging.getLogger(__name__)

_TEMPLATES = {
    "not_now": "Anlıyorum, isterseniz sadece 2 maddelik kısa bir analiz bırakabilirim.",
    "reject":  "Anladım, ileride ihtiyaç olursa memnuniyetle bakarız.",
}


async def generate_response(intent: str, lead: dict, audit: dict | None = None) -> str:
    """
    Returns a reply message string based on classified intent.
    not_now / reject → static template (no API call).
    positive / curious / price → Claude-generated, personalized.
    """
    if intent in _TEMPLATES:
        return _TEMPLATES[intent]

    prompt = build_reply_response_prompt(intent, lead, audit or {})
    result = await claude_api_call(prompt, max_tokens=200, temperature=0.3)
    text = (result or "").strip()

    if not text:
        # Inline fallbacks — should rarely trigger
        fallbacks = {
            "positive": "Çok iyi, 10–15 dakikalık kısa bir görüşmede bunu net şekilde gösterebilirim. Size ne zaman uygun olur?",
            "curious":  "Aslında çok basit — birkaç somut noktayı sizin örneğiniz üzerinden gösterebilirim.",
            "price":    "Önce nerede kayıp olduğunu net görmek daha doğru olur, çünkü her işletmede farklı çıkıyor.",
        }
        text = fallbacks.get(intent, "Size daha fazla bilgi verebilirim, ne zaman uygun olur?")

    logger.info("Response uretildi: lead=%s intent=%s", lead.get("isim"), intent)
    return text
