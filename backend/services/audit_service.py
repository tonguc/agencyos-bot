"""
Audit Service — orchestration only.
Calls core (audit_generator, hook_engine) + repositories + logs.
No FastAPI, ARQ, or Telegram imports.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from core.audit_generator import generate_audit
from core.beauty_subsector import detect_beauty_subsector
from core.clinic_subsector import detect_clinic_subsector
from core.education_subsector import detect_education_subsector
from core.lawyer_subsector import detect_lawyer_subsector
from core.real_estate_subsector import detect_real_estate_subsector
from core.hook_engine import select_and_generate_hook
from core.lead_scorer import calculate_final_score
from core.playbook import load_playbook
from core.website_update_detector import detect_website_update
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

    sector = lead.sector or "klinik"
    lead_dict = lead_to_core_dict(lead)

    # Alt sektör tespiti — playbook seçimini etkiler
    if sector == "klinik":
        subsector = detect_clinic_subsector(lead_dict)
        lead_dict["clinic_subsector"] = subsector
        playbook = load_playbook(f"clinic_{subsector}")
        logger.info("Clinic subsector: lead=%s subsector=%s", str(lead_id)[:8], subsector)
    elif sector == "avukat":
        subsector = detect_lawyer_subsector(lead_dict)
        lead_dict["sub_sector"] = subsector
        playbook = load_playbook(f"lawyer_{subsector}")
        logger.info("Lawyer subsector: lead=%s subsector=%s", str(lead_id)[:8], subsector)
    elif sector == "emlak":
        subsector = detect_real_estate_subsector(lead_dict)
        lead_dict["sub_sector"] = subsector
        playbook = load_playbook(f"real_estate_{subsector}")
        logger.info("Real estate subsector: lead=%s subsector=%s", str(lead_id)[:8], subsector)
    elif sector == "guzellik":
        subsector = detect_beauty_subsector(lead_dict)
        lead_dict["sub_sector"] = subsector
        playbook = load_playbook(f"beauty_{subsector}")
        logger.info("Beauty subsector: lead=%s subsector=%s", str(lead_id)[:8], subsector)
    elif sector == "egitim":
        subsector = detect_education_subsector(lead_dict)
        lead_dict["sub_sector"] = subsector
        playbook = load_playbook(f"education_{subsector}")
        logger.info("Education subsector: lead=%s subsector=%s", str(lead_id)[:8], subsector)
    else:
        playbook = load_playbook(sector)

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

    # Website güncelleme tespiti (sitemap/blog/header/footer)
    update_info = await detect_website_update(lead.website or "")
    lead_dict["last_website_update_days"] = update_info["last_update_days"]
    lead_dict["website_update_confidence"] = update_info["confidence"]
    logger.info(
        "Website update: lead=%s days=%s conf=%.1f source=%s",
        str(lead_id)[:8], update_info["last_update_days"],
        update_info["confidence"], update_info["source"],
    )

    audit_for_scorer = {
        **audit_result,
        "pagespeed": site_data.get("hiz_skoru"),
        "ssl": site_data.get("ssl"),
    }
    refined = calculate_final_score(lead_dict, audit_for_scorer, playbook)
    update_fields: dict = {"status": "Audit"}
    if refined["status"] == "ok":
        update_fields["opportunity_score"] = int(refined["final_score"])
        update_fields["priority"] = refined["priority"]
    await LeadRepository(db).update(lead, **update_fields)
    await log_event(db, event=ActivityEvent.AUDIT_COMPLETED,
                    lead_id=lead_id, data={"audit_id": str(audit.id),
                                           "score": audit_result.get("genel_skor")})
    logger.info("Audit tamamlandi: lead=%s score=%s", str(lead_id)[:8],
                audit_result.get("genel_skor"))
    return audit
