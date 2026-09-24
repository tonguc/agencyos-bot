"""
Audit Service — orchestration only.
Calls core (audit_generator, hook_engine) + repositories + logs.
No FastAPI, ARQ, or Telegram imports.
"""

import logging
import asyncio
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.audit_generator import generate_audit
from core.market_evidence import collect_market, commercial_evidence
from core.beauty_subsector import detect_beauty_subsector
from core.clinic_subsector import detect_clinic_subsector
from core.education_subsector import detect_education_subsector
from core.ev_hizmetleri_subsector import detect_ev_hizmetleri_subsector
from core.lawyer_subsector import detect_lawyer_subsector
from core.real_estate_subsector import detect_real_estate_subsector
from core.restaurant_subsector import detect_restaurant_subsector
from core.hook_engine import select_and_generate_hook
from core.lead_scorer import calculate_final_score
from core.playbook import load_playbook
from core.sales_output_generator import generate_sales_output
from core.website_update_detector import detect_website_update
from models.activity_log import ActivityEvent
from models.audit import Audit
from repositories.audit import AuditRepository
from repositories.lead import LeadRepository
from services.activity import log_event
from services.lead_service import lead_to_core_dict

logger = logging.getLogger(__name__)

# Sektör alias'ları — eski/granüler sektör kodlarını ana sektöre yönlendirir
_CLINIC_ALIASES  = {"plastik_cerrah", "diyetisyen"}
_EV_HIZ_ALIASES  = {"tesisatci", "tesisat", "elektrikci", "elektrik", "boyaci", "tadilat"}


async def run_audit(
    lead_id: uuid.UUID,
    db: AsyncSession,
    since_dt: datetime | None = None,
) -> Audit:
    """Run full audit pipeline for a lead. Returns saved Audit ORM instance.

    since_dt: Bu zaman damgasından sonra zaten oluşturulmuş audit varsa onu döner
    (Claude/Apify çağrısı yapılmaz). ARQ retry idempotency için task'tan
    job.created_at geçirilir.
    """
    lead = await LeadRepository(db).get(lead_id)
    if not lead:
        raise ValueError(f"Lead bulunamadi: {lead_id}")

    if since_dt is not None:
        existing = await AuditRepository(db).get_latest_for_lead(lead_id, since_dt=since_dt)
        if existing:
            logger.info(
                "run_audit idempotent skip: lead=%s existing=%s (since=%s)",
                str(lead_id)[:8], str(existing.id)[:8], since_dt.isoformat(),
            )
            return existing

    sector = lead.sector or "klinik"
    lead_dict = lead_to_core_dict(lead)

    # Alias normalizasyonu
    if sector in _CLINIC_ALIASES:
        sector = "klinik"
    elif sector in _EV_HIZ_ALIASES:
        sector = "ev_hizmetleri"

    # Alt sektör tespiti — playbook seçimini etkiler
    # Eksik subsector playbook'unda top-level sector'e düşeriz (500 atmaz, audit devam).
    if sector == "klinik":
        subsector = detect_clinic_subsector(lead_dict)
        lead_dict["clinic_subsector"] = subsector
        playbook = load_playbook(f"clinic_{subsector}", fallback="clinic_general")
        logger.info("Clinic subsector: lead=%s subsector=%s", str(lead_id)[:8], subsector)

    elif sector == "avukat":
        subsector = detect_lawyer_subsector(lead_dict)
        lead_dict["sub_sector"] = subsector
        playbook = load_playbook(f"lawyer_{subsector}", fallback="lawyer_litigation")
        logger.info("Lawyer subsector: lead=%s subsector=%s", str(lead_id)[:8], subsector)

    elif sector == "emlak":
        subsector = detect_real_estate_subsector(lead_dict)
        lead_dict["sub_sector"] = subsector
        playbook = load_playbook(f"real_estate_{subsector}", fallback="real_estate_local")
        logger.info("Real estate subsector: lead=%s subsector=%s", str(lead_id)[:8], subsector)

    elif sector == "guzellik":
        subsector = detect_beauty_subsector(lead_dict)
        lead_dict["sub_sector"] = subsector
        playbook = load_playbook(f"beauty_{subsector}", fallback="beauty_routine")
        logger.info("Beauty subsector: lead=%s subsector=%s", str(lead_id)[:8], subsector)

    elif sector == "egitim":
        subsector = detect_education_subsector(lead_dict)
        lead_dict["sub_sector"] = subsector
        playbook = load_playbook(f"education_{subsector}", fallback="education_course")
        logger.info("Education subsector: lead=%s subsector=%s", str(lead_id)[:8], subsector)

    elif sector == "ev_hizmetleri":
        subsector = detect_ev_hizmetleri_subsector(lead_dict)
        lead_dict["sub_sector"] = subsector
        playbook = load_playbook(f"ev_hizmetleri_{subsector}", fallback="ev_hizmetleri_tesisat")
        logger.info("Ev hizmetleri subsector: lead=%s subsector=%s", str(lead_id)[:8], subsector)

    elif sector == "restoran":
        subsector = detect_restaurant_subsector(lead_dict)
        lead_dict["sub_sector"] = subsector
        playbook = load_playbook(f"restaurant_{subsector}", fallback="clinic_general")
        logger.info("Restaurant subsector: lead=%s subsector=%s", str(lead_id)[:8], subsector)

    else:
        # kadin_dogum ve bilinmeyen sektörler doğrudan playbook'larına gider
        playbook = load_playbook(sector, fallback="clinic_general")

    market_lead = {**lead_dict, "city": lead.city, "district": lead.district, "review_count": lead.review_count}
    audit_result, market = await asyncio.gather(
        generate_audit(lead_dict, playbook), collect_market(market_lead),
    )
    audit_result["market_evidence"] = market
    audit_result["commercial_evidence"] = commercial_evidence(market_lead, market, audit_result)
    hook = await select_and_generate_hook(lead_dict, audit_result, playbook)

    sales_output = await generate_sales_output(lead_dict, audit_result, playbook)
    audit_result["sales_output"] = sales_output

    skorlar = audit_result.get("skorlar") or {}
    killer = audit_result.get("killer_insight") or {}
    site_data = audit_result.get("_site_data") or {}

    audit = await AuditRepository(db).create(
        lead_id=lead_id,
        site_speed=site_data.get("hiz_skoru"),
        site_title=site_data.get("title"),
        site_meta=site_data.get("meta"),
        site_h1=site_data.get("h1"),
        has_form=site_data.get("form_var"),
        has_tel=site_data.get("tel_var"),
        has_ssl=site_data.get("ssl"),
        result=audit_result,
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

    update_info = await detect_website_update(lead.website or "")
    lead_dict["last_website_update_days"] = update_info["last_update_days"]
    lead_dict["website_update_confidence"] = update_info["confidence"]
    logger.info(
        "Website update: lead=%s days=%s conf=%.1f source=%s",
        str(lead_id)[:8], update_info["last_update_days"],
        update_info["confidence"], update_info["source"],
    )

    # Site analysis sinyallerini lead_dict'e aktar (advanced_signals için)
    lead_dict["has_cta"] = site_data.get("form_var") or lead_dict.get("has_cta")
    lead_dict["has_form"] = site_data.get("form_var")
    lead_dict["has_viewport"] = site_data.get("viewport_present")
    if site_data.get("hiz_skoru") is not None:
        lead_dict["_pagespeed"] = site_data.get("hiz_skoru")

    audit_for_scorer = {
        **audit_result,
        "pagespeed": site_data.get("hiz_skoru"),
        "ssl": site_data.get("ssl"),
        "_serp_data": market if market.get("status") == "complete" else {},
    }
    # Audit aşamasında hard_filter'ı atla — kullanıcı bu lead'i seçti.
    # "telefon yok" gibi sebeplerle skoru null bırakmak yerine her zaman hesapla.
    refined = calculate_final_score(
        lead_dict, audit_for_scorer, playbook, skip_hard_filter=True,
    )
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
