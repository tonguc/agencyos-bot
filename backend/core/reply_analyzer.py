"""
Reply Analyzer — Hybrid intent classification.
Keyword scoring first; Claude fallback when confidence < 0.70 or signals conflict.
"""

import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

INTENT_POSITIVE = "positive"
INTENT_CURIOUS  = "curious"
INTENT_PRICE    = "price"
INTENT_NOT_NOW  = "not_now"
INTENT_REJECT   = "reject"

KEYWORD_PATTERNS: dict[str, list[str]] = {
    INTENT_POSITIVE: [
        r"\bevet\b", r"konuşalım", r"konusalim", r"bilgi al",
        r"ilgileniyorum", r"anlat", r"ne zaman uygun", r"\btamam\b",
        r"\bolur\b", r"iyi fikir", r"güzel düşünce", r"merak ettim",
    ],
    INTENT_CURIOUS: [
        r"nasıl", r"nasil", r"ne demek", r"anlamadım", r"anlamadim",
        r"daha fazla", r"detay ver", r"açıkla", r"acikla",
        r"nedir bu", r"ne yapıyorsun", r"ne yapiyorsun",
    ],
    INTENT_PRICE: [
        r"fiyat", r"ücret", r"ucret", r"para", r"kaç lira", r"kac lira",
        r"kaç tl", r"kac tl", r"maliyet", r"ne kadar tutar", r"bütçe", r"butce",
    ],
    INTENT_NOT_NOW: [
        r"şu an", r"su an", r"şimdi değil", r"simdi degil",
        r"meşgulüm", r"mesgulyum", r"yoğunuz", r"yogunuz",
        r"daha sonra", r"ileride", r"bekleyebilir",
        r"uygun değil", r"uygun degil", r"ay.{0,5}sonra", r"hafta.{0,5}sonra",
    ],
    INTENT_REJECT: [
        r"ilgilenmiyorum", r"gerek yok", r"istemiyorum",
        r"\bhayır\b", r"\bhayir\b", r"mesaj atmayın", r"mesaj atmayin",
        r"\bbırakın\b", r"\birakin\b", r"\bspam\b",
    ],
}

CLAUDE_FALLBACK_THRESHOLD = 0.70


@dataclass
class ReplyAnalysis:
    intent: str
    confidence: float


async def analyze_reply(message: str) -> ReplyAnalysis:
    """Classify reply intent. Uses Claude when keyword confidence is low."""
    result = _keyword_classify(message)
    logger.debug("Keyword classify: intent=%s conf=%.2f", result.intent, result.confidence)

    if result.confidence < CLAUDE_FALLBACK_THRESHOLD or _needs_claude(message, result):
        logger.info("Reply analyzer: Claude fallback triggered (conf=%.2f)", result.confidence)
        result = await _claude_classify(message)

    return result


def _keyword_classify(message: str) -> ReplyAnalysis:
    text = message.lower()
    scores = {
        intent: sum(1 for p in patterns if re.search(p, text))
        for intent, patterns in KEYWORD_PATTERNS.items()
    }

    top_intent = max(scores, key=scores.get)
    top_hits = scores[top_intent]

    if top_hits == 0:
        return ReplyAnalysis(intent=INTENT_CURIOUS, confidence=0.40)

    sorted_hits = sorted(scores.values(), reverse=True)
    second_hits = sorted_hits[1] if len(sorted_hits) > 1 else 0

    confidence = min(0.95, 0.55 + top_hits * 0.10)
    if top_hits - second_hits <= 1:
        confidence -= 0.15

    return ReplyAnalysis(intent=top_intent, confidence=round(max(0.35, confidence), 2))


def _needs_claude(message: str, result: ReplyAnalysis) -> bool:
    """Force Claude for ambiguous patterns regardless of confidence score."""
    text = message.lower()
    # Price + agreement together: "fiyat nedir evet düşünebiliriz"
    if re.search(r"fiyat|ücret|maliyet", text) and re.search(r"\bevet\b|\btamam\b|\bolur\b", text):
        return True
    # Very short replies need context Claude can infer but keywords can't
    if len(message.split()) <= 2 and result.intent not in (INTENT_REJECT, INTENT_POSITIVE):
        return True
    return False


async def _claude_classify(message: str) -> ReplyAnalysis:
    from core.utils import claude_api_call, safe_json_parse
    prompt = (
        "Aşağıdaki müşteri mesajını intent'e göre sınıflandır.\n"
        "Olası intent'ler: positive, curious, price, not_now, reject\n"
        "Sadece JSON döndür, başka açıklama yazma:\n"
        '{"intent": "...", "confidence": 0.0}\n\n'
        f"Mesaj: {message}"
    )
    raw = await claude_api_call(prompt, max_tokens=60, temperature=0)
    parsed = safe_json_parse(raw, fallback={"intent": INTENT_CURIOUS, "confidence": 0.5})
    return ReplyAnalysis(
        intent=parsed.get("intent", INTENT_CURIOUS),
        confidence=float(parsed.get("confidence", 0.5)),
    )
