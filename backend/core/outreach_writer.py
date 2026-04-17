import logging

from core.utils import safe_json_parse, API_SEMAPHORE, claude_api_call
from core.prompts import build_outreach_prompt, build_followup_prompt

logger = logging.getLogger(__name__)

ONERILEN_MAP = {"data_hook": "v4", "gap_hook": "v4", "money_hook": "v4"}

VERSIYONLAR = ("v1", "v2", "v3", "v4")

FALLBACK_OUTREACH = {
    "v1": "Mesaj uretilemedi",
    "v2": "Mesaj uretilemedi",
    "v3": "Mesaj uretilemedi",
    "v4": "Mesaj uretilemedi",
    "onerilen": "v4",
}


async def write_outreach(lead: dict, audit: dict, hook: dict, playbook: dict) -> dict:
    async with API_SEMAPHORE:
        varsayilan = ONERILEN_MAP.get(hook["tip"], "v1")
        prompt = build_outreach_prompt(lead, audit, hook, playbook, varsayilan)

        response = await claude_api_call(prompt, max_tokens=1200, temperature=0.3)
        result = safe_json_parse(response, fallback=dict(FALLBACK_OUTREACH))

        for k, v in FALLBACK_OUTREACH.items():
            result.setdefault(k, v)

        if result.get("onerilen") not in VERSIYONLAR:
            result["onerilen"] = varsayilan

        logger.info(
            "Outreach uretildi: %s | onerilen=%s",
            lead.get("isim"), result.get("onerilen"),
        )
        return result


async def write_followup(lead: dict, gun: int, onceki: str, playbook: dict) -> str:
    async with API_SEMAPHORE:
        prompt = build_followup_prompt(lead, gun, onceki, playbook)
        result = await claude_api_call(prompt, max_tokens=300, temperature=0.3)
        logger.info("Followup uretildi: %s | gun=%d", lead.get("isim"), gun)
        return (result or "Takip mesaji uretilemedi").strip()
