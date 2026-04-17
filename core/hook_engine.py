import re
import logging

from core.utils import API_SEMAPHORE, claude_api_call
from core.prompts import build_data_hook_prompt, build_gap_hook_prompt

logger = logging.getLogger(__name__)


async def select_and_generate_hook(lead: dict, audit: dict, playbook: dict) -> dict:
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

    if lead.get("website") and audit.get("genel_skor", 100) < 50:
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
    yorum = lead.get("yorum_sayisi") or 0
    trafik = "dusuk" if yorum < 10 else "orta" if yorum < 50 else "yuksek"
    mantik = playbook["hook_mantigi"]
    aralik = mantik[f"{trafik}_aralik"]
    guven = mantik["varsayilan_guven"]

    m = re.match(r"\s*(\d+)\s*-\s*(\d+)", aralik)
    mi, ma = (m.group(1), m.group(2)) if m else ("10", "20")

    sablon = playbook["hook_tipleri"]["money_hook"]["sablon"]
    return (
        sablon.replace("{min}", mi)
        .replace("{max}", ma)
        .replace("{guven}", str(guven))
    )
