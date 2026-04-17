import os
import re
import json
import logging
import asyncio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("agencyos.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)


ICP_STRICT_MODE = os.getenv("ICP_STRICT_MODE", "false").lower() == "true"

API_SEMAPHORE = asyncio.Semaphore(3)


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

    logger.warning(
        "safe_json_parse failed, returning fallback. Ham cikti (ilk 500 char): %r",
        (text or "")[:500],
    )
    return fallback


def validate_playbook(playbook: dict) -> tuple[bool, list[str]]:
    errors = []

    required_fields = [
        "sektor",
        "display_name",
        "kpi_listesi",
        "hook_tipleri",
        "audit_kriterleri",
        "icp_filtre",
        "outreach",
        "hook_mantigi",
    ]

    if not isinstance(playbook, dict):
        return False, ["playbook bir dict olmalı"]

    for field in required_fields:
        if field not in playbook:
            errors.append(f"Zorunlu alan eksik: {field}")

    hook_tipleri = playbook.get("hook_tipleri", {})
    if isinstance(hook_tipleri, dict):
        required_hooks = ["data_hook", "gap_hook", "money_hook"]
        for hook in required_hooks:
            if hook not in hook_tipleri:
                errors.append(f"Hook tipi eksik: {hook}")
    else:
        errors.append("hook_tipleri bir dict olmalı")

    icp_filtre = playbook.get("icp_filtre", {})
    if isinstance(icp_filtre, dict):
        required_icp = ["yorum_min", "yorum_max", "oncelikli_ilceler"]
        for field in required_icp:
            if field not in icp_filtre:
                errors.append(f"ICP filtre alanı eksik: {field}")
    else:
        errors.append("icp_filtre bir dict olmalı")

    return len(errors) == 0, errors


_anthropic_client = None
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")


def _get_claude_client():
    global _anthropic_client
    if _anthropic_client is not None:
        return _anthropic_client
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        logger.error("CLAUDE_API_KEY .env'de tanımlı değil")
        return None
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        logger.error("'anthropic' paketi yüklü değil — pip install anthropic")
        return None
    _anthropic_client = AsyncAnthropic(api_key=api_key)
    return _anthropic_client


async def claude_api_call(
    prompt: str,
    max_tokens: int = 1000,
    temperature: float = 0.2,
    model: str | None = None,
    prefill: str | None = None,
) -> str:
    client = _get_claude_client()
    if client is None:
        return ""
    messages: list[dict] = [{"role": "user", "content": prompt}]
    if prefill:
        messages.append({"role": "assistant", "content": prefill})
    try:
        msg = await client.messages.create(
            model=model or CLAUDE_MODEL,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
        )
        parts = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
        text = "".join(parts)
        return (prefill + text) if prefill else text
    except Exception as e:
        logger.exception(f"Claude API çağrısı başarısız: {e}")
        return ""


async def batch_audit(items: list, audit_fn, *args, **kwargs) -> list:
    async def _run(item):
        async with API_SEMAPHORE:
            try:
                return await audit_fn(item, *args, **kwargs)
            except Exception as e:
                logger.exception(f"batch_audit item failed: {e}")
                return {"error": str(e), "item": item}

    return await asyncio.gather(*[_run(item) for item in items])
