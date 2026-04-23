"""
Core utilities — framework-agnostic.
No FastAPI, ARQ, or Telegram imports allowed here.
"""

import asyncio
import json
import logging
import re

logger = logging.getLogger(__name__)

API_SEMAPHORE = asyncio.Semaphore(3)

_anthropic_client = None


def safe_json_parse(text: str, fallback=None):
    if fallback is None:
        fallback = {}
    if not text or not isinstance(text, str):
        return fallback
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    logger.warning("safe_json_parse failed. Ham cikti (ilk 300): %r", (text or "")[:300])
    return fallback


def validate_playbook(playbook: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(playbook, dict):
        return False, ["playbook bir dict olmali"]
    for field in ["sektor", "display_name", "kpi_listesi", "hook_tipleri",
                  "audit_kriterleri", "icp_filtre", "outreach", "hook_mantigi"]:
        if field not in playbook:
            errors.append(f"Zorunlu alan eksik: {field}")
    if isinstance(playbook.get("hook_tipleri"), dict):
        for h in ["data_hook", "gap_hook", "money_hook"]:
            if h not in playbook["hook_tipleri"]:
                errors.append(f"Hook tipi eksik: {h}")
    if isinstance(playbook.get("icp_filtre"), dict):
        for f in ["yorum_min", "yorum_max", "oncelikli_ilceler"]:
            if f not in playbook["icp_filtre"]:
                errors.append(f"ICP filtre alani eksik: {f}")
    return len(errors) == 0, errors


def _get_claude_client():
    global _anthropic_client
    if _anthropic_client is not None:
        return _anthropic_client
    from config import settings
    if not settings.CLAUDE_API_KEY:
        logger.error("CLAUDE_API_KEY tanimli degil")
        return None
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        logger.error("'anthropic' paketi yuklu degil")
        return None
    _anthropic_client = AsyncAnthropic(api_key=settings.CLAUDE_API_KEY)
    return _anthropic_client


async def claude_api_call(
    prompt: str,
    max_tokens: int = 1000,
    temperature: float = 0.2,
    model: str | None = None,
    prefill: str | None = None,
) -> str:
    from config import settings
    client = _get_claude_client()
    if client is None:
        return ""
    messages: list[dict] = [{"role": "user", "content": prompt}]
    if prefill:
        messages.append({"role": "assistant", "content": prefill})
    try:
        msg = await client.messages.create(
            model=model or settings.CLAUDE_MODEL,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
            timeout=90.0,
        )
        parts = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
        text = "".join(parts)
        return (prefill + text) if prefill else text
    except Exception as e:
        # request_id response header'inda geliyor, ama exception path'te alamiyoruz;
        # support icin mesaj tipini (rate_limit/overloaded/timeout) net logla.
        logger.exception("Claude API cagrisi basarisiz: %s", e)
        return ""
