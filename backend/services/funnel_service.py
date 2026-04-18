"""
Funnel Service — full sales funnel orchestration.
Coordinates: reply analysis → response generation → follow-up sequencing → close.
No FastAPI / ARQ / Telegram imports.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from core.beauty_subsector import detect_beauty_subsector
from core.clinic_subsector import detect_clinic_subsector
from core.close_engine import generate_close_message
from core.education_subsector import detect_education_subsector
from core.ev_hizmetleri_subsector import detect_ev_hizmetleri_subsector
from core.lawyer_subsector import detect_lawyer_subsector
from core.outreach_writer import write_followup, write_initial_message
from core.playbook import load_playbook
from core.real_estate_subsector import detect_real_estate_subsector
from core.reply_analyzer import analyze_reply
from core.response_engine import generate_response
from models.activity_log import ActivityEvent
from models.lead import Lead
from repositories.lead import LeadRepository
from repositories.outreach import OutreachRepository
from services.activity import log_event
from services.lead_service import lead_to_core_dict

logger = logging.getLogger(__name__)

# Maps followup_stage → day number passed to write_followup()
_FOLLOWUP_DAY = {1: 2, 2: 4, 3: 7}

_HOT_PRIORITIES  = {"yuksek"}
_WARM_PRIORITIES = {"orta"}

_CLINIC_ALIASES = {"plastik_cerrah", "diyetisyen"}
_EV_HIZ_ALIASES = {"tesisatci", "tesisat", "elektrikci", "elektrik", "boyaci", "tadilat"}


def _resolve_playbook(lead_dict: dict) -> dict:
    """Detect sub-sector and load the correct playbook — mirrors audit_service routing."""
    sector = lead_dict.get("sektor") or "klinik"

    # Alias normalizasyonu
    if sector in _CLINIC_ALIASES:
        sector = "klinik"
    elif sector in _EV_HIZ_ALIASES:
        sector = "ev_hizmetleri"

    if sector == "klinik":
        sub = detect_clinic_subsector(lead_dict)
        lead_dict["clinic_subsector"] = sub
        return load_playbook(f"clinic_{sub}")

    if sector == "avukat":
        sub = detect_lawyer_subsector(lead_dict)
        lead_dict["sub_sector"] = sub
        return load_playbook(f"lawyer_{sub}")

    if sector == "emlak":
        sub = detect_real_estate_subsector(lead_dict)
        lead_dict["sub_sector"] = sub
        return load_playbook(f"real_estate_{sub}")

    if sector == "guzellik":
        sub = detect_beauty_subsector(lead_dict)
        lead_dict["sub_sector"] = sub
        return load_playbook(f"beauty_{sub}")

    if sector == "egitim":
        sub = detect_education_subsector(lead_dict)
        lead_dict["sub_sector"] = sub
        return load_playbook(f"education_{sub}")

    if sector == "ev_hizmetleri":
        sub = detect_ev_hizmetleri_subsector(lead_dict)
        lead_dict["sub_sector"] = sub
        return load_playbook(f"ev_hizmetleri_{sub}")

    return load_playbook(sector)


async def send_initial_outreach(
    lead_id: uuid.UUID,
    audit: dict,
    hook: dict,
    db: AsyncSession,
) -> str:
    """Generate the single-message initial outreach for automated sending.
    Resolves sub-sector and playbook internally."""
    lead = await LeadRepository(db).get(lead_id)
    if not lead:
        raise ValueError(f"Lead bulunamadi: {lead_id}")

    lead_dict = lead_to_core_dict(lead)
    playbook = _resolve_playbook(lead_dict)
    text = await write_initial_message(lead_dict, audit, hook, playbook)

    await log_event(
        db,
        event=ActivityEvent.MESSAGE_SENT,
        lead_id=lead_id,
        data={"channel": playbook.get("outreach", {}).get("kanal", "unknown"), "type": "initial"},
    )
    logger.info("Initial outreach uretildi: lead=%s sector=%s", str(lead_id)[:8], lead_dict.get("sektor"))
    return text


async def handle_reply(
    outreach_id: uuid.UUID,
    reply_text: str,
    db: AsyncSession,
    audit: dict | None = None,
) -> dict:
    """
    Analyze an incoming reply, persist intent, generate contextual response.

    Returns:
        {
            "intent": str,
            "confidence": float,
            "response_text": str,
            "close_message": str | None,   # only for positive intent
        }
    """
    repo = OutreachRepository(db)
    outreach = await repo.get(outreach_id)
    if not outreach:
        raise ValueError(f"OutreachMessage bulunamadi: {outreach_id}")

    lead = await LeadRepository(db).get(outreach.lead_id)
    if not lead:
        raise ValueError(f"Lead bulunamadi: {outreach.lead_id}")

    lead_dict = lead_to_core_dict(lead)

    analysis = await analyze_reply(reply_text)
    await repo.update_reply(outreach, reply_text, analysis.intent, analysis.confidence)
    await LeadRepository(db).update(lead, status="Cevap")

    response_text = await generate_response(analysis.intent, lead_dict, audit or {})

    close_msg = None
    if analysis.intent == "positive":
        close_msg = await generate_close_message(lead_dict)

    await log_event(
        db,
        event=ActivityEvent.REPLY_RECEIVED,
        lead_id=outreach.lead_id,
        data={
            "outreach_id": str(outreach_id),
            "intent": analysis.intent,
            "confidence": analysis.confidence,
        },
    )
    logger.info(
        "Reply islendi: lead=%s intent=%s conf=%.2f",
        str(outreach.lead_id)[:8], analysis.intent, analysis.confidence,
    )
    return {
        "intent": analysis.intent,
        "confidence": analysis.confidence,
        "response_text": response_text,
        "close_message": close_msg,
    }


async def get_next_followup(
    outreach_id: uuid.UUID,
    db: AsyncSession,
) -> dict | None:
    """
    Generate the next follow-up in the sequence (stage 1→2→3).
    Resolves playbook internally. Returns None when sequence is done or reply received.

    Returns:
        {"stage": int, "day": int, "text": str} or None
    """
    repo = OutreachRepository(db)
    outreach = await repo.get(outreach_id)
    if not outreach:
        raise ValueError(f"OutreachMessage bulunamadi: {outreach_id}")

    if outreach.reply_intent is not None:
        return None

    next_stage = outreach.followup_stage + 1
    if next_stage > 3:
        return None

    lead = await LeadRepository(db).get(outreach.lead_id)
    if not lead:
        raise ValueError(f"Lead bulunamadi: {outreach.lead_id}")

    lead_dict = lead_to_core_dict(lead)
    playbook = _resolve_playbook(lead_dict)
    prev_text = outreach.v4 or outreach.v1 or ""
    day = _FOLLOWUP_DAY[next_stage]

    text = await write_followup(lead_dict, day, prev_text, playbook)
    await repo.update_followup_stage(outreach, next_stage)

    logger.info(
        "Followup uretildi: lead=%s stage=%d day=%d",
        str(outreach.lead_id)[:8], next_stage, day,
    )
    return {"stage": next_stage, "day": day, "text": text}


async def get_priority_queue(db: AsyncSession) -> dict[str, list[Lead]]:
    """Returns leads bucketed by send priority (HOT / WARM)."""
    lead_repo = LeadRepository(db)
    all_hot = await lead_repo.get_hot(limit=50)
    return {
        "hot":  [l for l in all_hot if l.priority in _HOT_PRIORITIES],
        "warm": [l for l in all_hot if l.priority in _WARM_PRIORITIES],
    }
