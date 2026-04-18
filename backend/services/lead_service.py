"""
Lead Service — orchestration only.
Calls core (pure logic) + repositories (DB) + logs activity.
No FastAPI, ARQ, or Telegram imports.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from core.lead_collector import collect_google_maps
from core.icp_filter import filter_leads
from core.lead_scorer import calculate_final_score
from core.playbook import load_playbook
from models.activity_log import ActivityEvent
from repositories.lead import LeadRepository
from services.activity import log_event

logger = logging.getLogger(__name__)


def lead_to_core_dict(lead) -> dict:
    """Convert Lead ORM instance to the dict format core functions expect."""
    district = lead.district or ""
    city = lead.city or ""
    address = lead.address or f"{district}, {city}".strip(", ")
    return {
        "page_id": str(lead.id),
        "isim": lead.name or "",
        "sektor": lead.sector or "",
        "adres": address,
        "telefon": lead.phone,
        "website": lead.website,
        "yorum_sayisi": lead.review_count or 0,
        "puan": lead.google_rating or 0.0,
    }


async def collect_and_save(
    sector: str,
    city: str,
    district: str,
    limit: int,
    db: AsyncSession,
) -> dict:
    """Scrape leads → filter → score → save to DB. Returns summary dict."""
    playbook = load_playbook(sector)
    raw = await collect_google_maps(sector, city, district, limit=limit)
    if not raw:
        return {"saved": 0, "stats": {}, "error": "Apify sonuc dondurmedi"}

    filtered = filter_leads(raw, playbook)
    repo = LeadRepository(db)
    saved = 0

    scores = []
    for lead_data in filtered["nitelikli"]:
        score = calculate_final_score(lead_data, {}, playbook)
        if score["status"] == "rejected":
            logger.warning("Final scorer eledi (scrape): %s | %s", lead_data.get("isim"), score["reason"])
            continue
        await repo.create(
            name=lead_data.get("isim") or "",
            sector=sector,
            city=city,
            district=lead_data.get("ilce") or district or "",
            address=lead_data.get("adres"),
            phone=lead_data.get("telefon"),
            website=lead_data.get("website"),
            source="google_maps",
            source_data=lead_data,
            google_rating=lead_data.get("puan"),
            review_count=lead_data.get("yorum_sayisi"),
            opportunity_score=int(score["final_score"]),
            priority=score["priority"],
            status="Yeni",
        )
        scores.append(score["final_score"])
        saved += 1

    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    logger.info("collect_and_save: %d/%d kayit edildi | sektor=%s sehir=%s",
                saved, len(filtered["nitelikli"]), sector, city)
    return {"saved": saved, "avg_score": avg_score, "stats": filtered["istatistik"]}


async def update_status(lead_id: uuid.UUID, status: str, db: AsyncSession) -> bool:
    repo = LeadRepository(db)
    lead = await repo.get(lead_id)
    if not lead:
        return False
    await repo.update(lead, status=status)
    await log_event(db, event=ActivityEvent.LEAD_STATUS_CHANGED,
                    lead_id=lead_id, data={"status": status})
    return True
