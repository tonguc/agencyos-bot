"""Cost tracker — external API spend logging + budget alarm.

Tum hook'lar fail-safe (DB write fail caller flow'u kirmaz). Cagrilis:

  await record_claude(input_tokens=N, output_tokens=M, model="claude-sonnet-4-6")
  await record_apify(places=20, reviews=10)
  await record_openai_tts(chars=1200, model="tts-1")
  await record_openai_stt(seconds=8.5, model="whisper-1")

Fiyat tablosu core/pricing.py'da — pure, unit test edilebilir.
"""

import logging

from config import settings
from core.pricing import (
    claude_cost, apify_cost, openai_tts_cost, openai_stt_cost,
)
from database import AsyncSessionFactory
from repositories.api_usage import ApiUsageRepository
from services.notify import notify_admin

logger = logging.getLogger(__name__)


async def _safe_log(provider: str, **fields) -> None:
    try:
        async with AsyncSessionFactory() as db:
            await ApiUsageRepository(db).create(provider=provider, **fields)
            await db.commit()
    except Exception:
        # Cost logging hicbir flow'u kirmamali.
        logger.exception("cost_tracker._safe_log failed | provider=%s", provider)


async def record_claude(
    *, input_tokens: int, output_tokens: int, model: str, meta: dict | None = None
) -> None:
    cost = claude_cost(input_tokens, output_tokens, model)
    await _safe_log(
        "claude",
        tokens_in=input_tokens, tokens_out=output_tokens,
        cost_usd=cost, meta={"model": model, **(meta or {})},
    )
    await _maybe_alert("claude", cost)


async def record_apify(*, places: int, reviews: int = 0, meta: dict | None = None) -> None:
    cost = apify_cost(places, reviews)
    await _safe_log(
        "apify",
        units=float(places), cost_usd=cost,
        meta={"places": places, "reviews": reviews, **(meta or {})},
    )
    await _maybe_alert("apify", cost)


async def record_openai_tts(*, chars: int, model: str = "tts-1") -> None:
    cost = openai_tts_cost(chars)
    await _safe_log(
        "openai_tts",
        units=float(chars), cost_usd=cost, meta={"model": model},
    )
    await _maybe_alert("openai_tts", cost)


async def record_openai_stt(*, seconds: float, model: str = "whisper-1") -> None:
    cost = openai_stt_cost(seconds)
    await _safe_log(
        "openai_stt",
        units=seconds, cost_usd=cost, meta={"model": model},
    )
    await _maybe_alert("openai_stt", cost)


async def _maybe_alert(provider: str, last_call_cost: float) -> None:
    """Daily budget'in %80'i asilirsa admin alarm. DAILY_BUDGET_USD=0 ise atlanir."""
    budget = settings.DAILY_BUDGET_USD
    if budget <= 0:
        return
    try:
        async with AsyncSessionFactory() as db:
            spend = await ApiUsageRepository(db).daily_spend()
        total = sum(spend.values())
        pct = total / budget * 100.0
        if pct >= 80.0:
            await notify_admin(
                f"⚠️ GUNLUK BUTCE %{pct:.0f} ASILDI\n\n"
                f"Toplam: ${total:.2f} / ${budget:.2f}\n"
                f"Son cagri: {provider} ${last_call_cost:.4f}\n\n"
                f"Detay: " + ", ".join(f"{p}=${c:.2f}" for p, c in spend.items())
            )
    except Exception:
        logger.exception("cost_tracker._maybe_alert failed")

