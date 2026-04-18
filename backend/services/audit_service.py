"""
Audit Service — orchestration only.
Calls core (audit_generator, hook_engine) + repositories + logs.
No FastAPI, ARQ, or Telegram imports.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from core.audit_generator import generate_audit
from core.hook_engine import select_and_generate_hook
from core.opportunity_scorer import score_opportunity_with_audit
from core.playbook import load_playbook
from models.activity_log import ActivityEvent
from models.audit import Audit
from repositories.audit import AuditRepository
from repositories.lead import LeadRepository
from services.activity import log_event
from services.lead_service import lead_to_core_dict

logger = logging.getLogger(__name__)


async def run_audit(lead_id: uuid.UUID, db: AsyncSession) -> Audit:
    """Run full audit pipeline for a lead. Returns saved Audit ORM instance."""
    lead = await LeadRepository(db).get(lead_id)
    if not lead:
        raise ValueError(f"Lead bulunamadi: {lead_id}")

    playbook = load_playbook(lead.sector or "klinik")
    lead_dict = lead_to_core_dict(lead)

    audit_result = await generate_audit(lead_dict, playbook)
    hook = await select_and_generate_hook(lead_dict, audit_result, playbook)

    skorlar = audit_result.get("skorlar") or {}
    killer = audit_result.get("killer_insight") or {}
    site_data = audit_result.get("_site_data") or {}

    audit = await AuditRepository(db).create(
        lead_id=lead_id,
        # raw site data
        site_speed=site_data.get("hiz_skoru"),
        site_title=site_data.get("title"),
        site_meta=site_data.get("meta"),
        site_h1=site_data.get("h1"),
        has_form=site_data.get("form_var"),
        has_tel=site_data.get("tel_var"),
        has_ssl=site_data.get("ssl"),
        # full result
        result=audit_result,
        # denormalized
        general_score=audit_result.get("genel_skor"),
        ux_score=skorlar.get("ux"),
        seo_score=skorlar.get("seo"),
        conversion_score=skorlar.get("donusum"),
        urgency=audit_result.get("urgency"),
        lead_quality=audit_result.get("lead_kalitesi"),
        killer_insight=(killer.get("bulgu") or "")[:500],
        killer_metric=(killer.get("rakam") or "")[:100],
        personal_insight=audit_result.get("kisisel_insight"),
        hook_type=hook["tip"],
        hook_text=hook["hook"],
    )

    refined = score_opportunity_with_audit(
        base_score=lead.opportunity_score or 50,
        audit_result=audit_result,
        site_data=site_data,
    )
    await LeadRepository(db).update(
        lead,
        status="Audit",
        opportunity_score=refined["skor"],
        priority=refined["oncelik"],
    )
    await log_event(db, event=ActivityEvent.AUDIT_COMPLETED,
                    lead_id=lead_id, data={"audit_id": str(audit.id),
                                           "score": audit_result.get("genel_skor")})
    logger.info("Audit tamamlandi: lead=%s score=%s", str(lead_id)[:8],
                audit_result.get("genel_skor"))
    return audit
