"""
Funnel Service — full sales funnel orchestration.
Coordinates: reply analysis → response generation → follow-up sequencing → close.
No FastAPI / ARQ / Telegram imports.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from core.close_engine import generate_close_message
from core.outreach_writer import write_followup, write_initial_message
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

# Priority segments → HOT leads get immediate outreach
_HOT_PRIORITIES = {"yuksek"}
_WARM_PRIORITIES = {"orta"}


async def send_initial_outreach(
    lead_id: uuid.UUID,
    audit: dict,
    hook: dict,
    playbook: dict,
    db: AsyncSession,
) -> str:
    """Generate and persist the single-message initial outreach for automated sending."""
    lead = await LeadRepository(db).get(lead_id)
    if not lead:
        raise ValueError(f"Lead bulunamadi: {lead_id}")

    lead_dict = lead_to_core_dict(lead)
    text = await write_initial_message(lead_dict, audit, hook, playbook)

    await log_event(
        db,
        event=ActivityEvent.MESSAGE_SENT,
        lead_id=lead_id,
        data={"channel": playbook.get("outreach", {}).get("kanal", "unknown"), "type": "initial"},
    )
    logger.info("Initial outreach uretildi: lead=%s", str(lead_id)[:8])
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
    playbook: dict,
    db: AsyncSession,
) -> dict | None:
    """
    Generate the next follow-up message in the sequence (stage 1 → 2 → 3).
    Returns None if sequence is exhausted or a reply already came in.

    Returns:
        {"stage": int, "day": int, "text": str} or None
    """
    repo = OutreachRepository(db)
    outreach = await repo.get(outreach_id)
    if not outreach:
        raise ValueError(f"OutreachMessage bulunamadi: {outreach_id}")

    # Don't follow up if reply already received
    if outreach.reply_intent is not None:
        return None

    next_stage = outreach.followup_stage + 1
    if next_stage > 3:
        return None

    lead = await LeadRepository(db).get(outreach.lead_id)
    if not lead:
        raise ValueError(f"Lead bulunamadi: {outreach.lead_id}")

    lead_dict = lead_to_core_dict(lead)
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
    """
    Returns leads bucketed by send priority.
    HOT  → yuksek priority, Audit/Mesaj status
    WARM → orta priority, Audit/Mesaj status
    """
    lead_repo = LeadRepository(db)

    hot_leads = [
        l for l in await lead_repo.get_hot(limit=50)
        if l.priority in _HOT_PRIORITIES
    ]
    warm_leads = [
        l for l in await lead_repo.get_hot(limit=50)
        if l.priority in _WARM_PRIORITIES
    ]

    return {"hot": hot_leads, "warm": warm_leads}
