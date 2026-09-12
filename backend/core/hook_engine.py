import re
import logging

from core.utils import API_SEMAPHORE, claude_api_call
from core.prompts import build_data_hook_prompt, build_gap_hook_prompt

logger = logging.getLogger(__name__)


async def select_and_generate_hook(lead: dict, audit: dict, playbook: dict) -> dict:
    if not lead.get("website"):
        return {"tip": "gap_hook", "hook": "İncelediğim kayıtta web sitesi bağlantısını bulamadım. Kullandığınız bir web sitesi var mı?"}
    tip = _select_hook_type(lead, audit, playbook)
    logger.info("Hook secildi: %s | tip: %s", lead.get("isim"), tip)

    generators = {
        "data_hook": _generate_data_hook,
        "gap_hook": _generate_gap_hook,
        "money_hook": _generate_money_hook,
    }
    hook_text = await generators[tip](lead, audit, playbook)
    return {"tip": tip, "hook": hook_text}


def _select_hook_type(lead: dict, audit: dict, playbook: dict) -> str:
    rakip = audit.get("reklam_firsati", {}).get("rakip_durum", "yok")
    if rakip == "aktif":
        logger.debug("Hook: data_hook (rakip aktif)")
        return "data_hook"

    genel_skor = audit.get("genel_skor")
    if lead.get("website") and genel_skor is not None and genel_skor < 50:
        logger.debug("Hook: gap_hook (site var, skor dusuk)")
        return "gap_hook"

    logger.debug("Hook: money_hook (fallback)")
    return "money_hook"


def _ilce_from_adres(adres: str | None) -> str:
    if not adres:
        return "bolgenizde"
    parts = [p.strip() for p in adres.split(",") if p.strip()]
    return parts[0] if parts else "bolgenizde"


async def _generate_data_hook(lead: dict, audit: dict, playbook: dict) -> str:
    async with API_SEMAPHORE:
        prompt = build_data_hook_prompt(lead, audit, playbook, _ilce_from_adres(lead.get("adres")))
        result = await claude_api_call(prompt, max_tokens=150, temperature=0.1)
        return (result or playbook["hook_tipleri"]["data_hook"]["sablon"]).strip()


async def _generate_gap_hook(lead: dict, audit: dict, playbook: dict) -> str:
    async with API_SEMAPHORE:
        prompt = build_gap_hook_prompt(lead, audit, playbook, _ilce_from_adres(lead.get("adres")))
        result = await claude_api_call(prompt, max_tokens=150, temperature=0.1)
        return (result or playbook["hook_tipleri"]["gap_hook"]["sablon"]).strip()


async def _generate_money_hook(lead: dict, audit: dict, playbook: dict) -> str:
    # Review counts do not measure traffic, lost customers or confidence.
    return "İsterseniz sitenizin ziyaretçileri iletişime nasıl yönlendirdiğini birlikte değerlendirebiliriz."
