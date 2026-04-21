"""
Outreach Service — orchestration only.
No FastAPI, ARQ, or Telegram imports.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from core.hook_engine import select_and_generate_hook
from core.outreach_writer import write_outreach, write_followup
from core.playbook import load_playbook_for_sector
from models.activity_log import ActivityEvent
from models.outreach import OutreachMessage
from repositories.audit import AuditRepository
from repositories.lead import LeadRepository
from repositories.outreach import OutreachRepository
from services.activity import log_event
from services.lead_service import lead_to_core_dict

logger = logging.getLogger(__name__)


async def generate_outreach(lead_id: uuid.UUID, db: AsyncSession) -> OutreachMessage:
    """Generate 4-version outreach messages for a lead. Saves and returns ORM instance."""
    lead = await LeadRepository(db).get(lead_id)
    if not lead:
        raise ValueError(f"Lead bulunamadi: {lead_id}")

    playbook = load_playbook_for_sector(lead.sector or "klinik")
    lead_dict = lead_to_core_dict(lead)

    audit = await AuditRepository(db).get_latest_for_lead(lead_id)
    if audit:
        audit_dict = audit.result or {}
        hook = {"tip": audit.hook_type or "gap_hook", "hook": audit.hook_text or ""}
        if not hook["hook"]:
            hook = await select_and_generate_hook(lead_dict, audit_dict, playbook)
    else:
        audit_dict = _synthetic_audit(lead_dict)
        hook = await select_and_generate_hook(lead_dict, audit_dict, playbook)

    msgs = await write_outreach(lead_dict, audit_dict, hook, playbook)

    outreach = await OutreachRepository(db).create(
        lead_id=lead_id,
        audit_id=audit.id if audit else None,
        v1=msgs.get("v1"),
        v2=msgs.get("v2"),
        v3=msgs.get("v3"),
        v4=msgs.get("v4"),
        recommended=msgs.get("onerilen", "v4"),
    )

    await LeadRepository(db).update(lead, status="Mesaj")
    await log_event(db, event=ActivityEvent.OUTREACH_GENERATED,
                    lead_id=lead_id, data={"outreach_id": str(outreach.id)})
    return outreach


async def mark_sent(
    outreach_id: uuid.UUID,
    version: str,
    channel: str,
    db: AsyncSession,
) -> OutreachMessage:
    outreach = await OutreachRepository(db).get(outreach_id)
    if not outreach:
        raise ValueError(f"Outreach bulunamadi: {outreach_id}")
    updated = await OutreachRepository(db).update(
        outreach,
        sent_version=version,
        sent_at=datetime.now(timezone.utc),
        sent_channel=channel,
    )
    await log_event(db, event=ActivityEvent.MESSAGE_SENT,
                    lead_id=outreach.lead_id,
                    data={"version": version, "channel": channel})
    return updated


async def generate_followup(lead_id: uuid.UUID, db: AsyncSession) -> str:
    lead = await LeadRepository(db).get(lead_id)
    if not lead:
        raise ValueError(f"Lead bulunamadi: {lead_id}")
    playbook = load_playbook_for_sector(lead.sector or "klinik")
    outreach = await OutreachRepository(db).get_latest_for_lead(lead_id)
    prev_msg = ""
    if outreach and outreach.sent_version:
        prev_msg = getattr(outreach, outreach.sent_version, "") or ""
    days_since = 3
    if outreach and outreach.sent_at:
        delta = datetime.now(timezone.utc) - outreach.sent_at
        days_since = max(1, delta.days)
    text = await write_followup(lead_to_core_dict(lead), days_since, prev_msg, playbook)
    await log_event(db, event=ActivityEvent.FOLLOWUP_GENERATED,
                    lead_id=lead_id, data={"days": days_since})
    return text


def _synthetic_audit(lead_dict: dict) -> dict:
    """Minimal audit stub when no real audit exists."""
    eksikler = []
    has_ig = lead_dict.get("has_instagram", False)
    lcp = lead_dict.get("mobile_lcp")
    speed = lead_dict.get("mobile_speed_score")

    if not lead_dict.get("website"):
        if has_ig:
            eksikler.append("Instagram aktif ama web sitesi yok")
        else:
            eksikler.append("web sitesi yok")
    elif lcp is not None and lcp > 3.0:
        eksikler.append(f"mobil site yavaş (LCP {lcp:.1f} sn)")
    elif speed is not None and speed < 50:
        eksikler.append(f"mobil site yavaş ({speed}/100)")

    if (lead_dict.get("yorum_sayisi") or 0) < 10:
        eksikler.append(f"yorum düşük ({lead_dict.get('yorum_sayisi', 0)})")

    bulgu = " + ".join(eksikler) if eksikler else "dijital varlık zayıf"

    # Build a data-driven kisisel_insight when signals are available.
    # Tone: observation + possibility, no exact numbers or percentages.
    low = int(lcp) if lcp is not None else 0
    lcp_soft = f"{low}-{low + 1} sn civarı" if lcp is not None and lcp >= 2.0 else ""

    if has_ig and lcp is not None and lcp >= 2.0:
        kisisel = (
            f"Instagram'da aktif olduğunuzu gördüm. "
            f"Sitenize de baktım, mobilden biraz yavaş açılıyor ({lcp_soft}). "
            f"Instagram'dan gelen ziyaretçiler burada beklemeden çıkıyor olabilir."
        )
    elif has_ig and not lead_dict.get("website"):
        kisisel = (
            "Instagram'da aktif olduğunuzu gördüm — ama profilden gelen "
            "ziyaretçileri yönlendirecek bir site yok gibi görünüyor."
        )
    elif lcp is not None and lcp >= 2.0:
        kisisel = (
            f"Sitenize baktım, mobilden biraz yavaş açılıyor ({lcp_soft}). "
            f"Bu yüzden gelen ziyaretçilerin bir kısmı çıkıyor olabilir."
        )
    else:
        kisisel = ""

    return {
        "killer_insight": {"bulgu": bulgu, "etki": "musteri kaybi", "rakam": ""},
        "ux_hatalar": [], "seo_aciklar": [],
        "reklam_firsati": {"kanal": "", "aciklama": "", "rakip_durum": "yok"},
        "skorlar": {"ux": 0, "seo": 0, "donusum": 0},
        "urgency": "orta", "lead_kalitesi": "ilik",
        "genel_skor": 40, "en_acitan_nokta": bulgu,
        "kisisel_insight": kisisel, "_synthetic": True,
    }
