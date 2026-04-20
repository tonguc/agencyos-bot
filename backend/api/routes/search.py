import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.query_normalizer import build_search_cache_key, normalize_query, CACHE_TTL_SECONDS
from database import get_db
from repositories.lead import LeadRepository
from services.search_service import run_search

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])

_PRIORITY_TO_SEGMENT = {
    "yuksek": "hot",
    "orta":   "warm",
    "dusuk":  "review",  # DB leads are never "Elendi" — they passed the collection pipeline
}


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(20, ge=1, le=50)
    force_refresh: bool = False


async def _enrich_lead_ids(results: list[dict], db: AsyncSession) -> None:
    """Refresh lead_id and DB-sourced scores in-place.

    Always called — even on cache hits — so stale lead_id values from
    deleted leads never cause 404s on the detail page.
    """
    phones = [r["phone"] for r in results if r.get("phone")]
    if not phones:
        for r in results:
            r.setdefault("lead_id", None)
        return
    db_scores = await LeadRepository(db).find_scores_by_phones(phones)
    for r in results:
        phone    = r.get("phone") or ""
        db_entry = db_scores.get(phone)
        if not db_entry:
            r["lead_id"] = None
            continue
        r["lead_id"] = db_entry["id"]
        if db_entry["opportunity_score"] is not None:
            r["score"]    = db_entry["opportunity_score"]
            r["priority"] = db_entry["priority"]
            r["segment"]  = _PRIORITY_TO_SEGMENT.get(db_entry["priority"] or "", r["segment"])


def _calc_summary(results: list[dict]) -> dict:
    return {
        "hot":    sum(1 for r in results if r["segment"] == "hot"),
        "warm":   sum(1 for r in results if r["segment"] == "warm"),
        "ok":     sum(1 for r in results if r["segment"] == "ok"),
        "low":    sum(1 for r in results if r["segment"] == "low"),
        "review": sum(1 for r in results if r["segment"] == "review"),
        "total":  len(results),
    }


@router.post("/search")
async def search(
    body: SearchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    raw_query      = body.query
    normalized     = normalize_query(raw_query)
    cache_key      = build_search_cache_key(raw_query, body.limit)
    redis          = getattr(request.app.state, "arq_pool", None)

    # ── 1. Cache kontrol ────────────────────────────────────────────────
    if redis and not body.force_refresh:
        cached = await redis.get(cache_key)
        if cached:
            logger.info("[CACHE HIT] raw=%r normalized=%r key=%s", raw_query, normalized, cache_key)
            result  = json.loads(cached)
            results = result.get("results", [])
            # Always re-enrich from DB: cached lead_ids become stale when leads are
            # deleted or after a DB reset, causing 404s on the detail page.
            await _enrich_lead_ids(results, db)
            result["summary"]    = _calc_summary(results)
            result["cache_hit"]  = True
            return result

    logger.info("[CACHE MISS] raw=%r normalized=%r key=%s", raw_query, normalized, cache_key)

    # ── 2. Arama ────────────────────────────────────────────────────────
    logger.info("[APIFY CALL] key=%s", cache_key)
    result = await run_search(raw_query, limit=body.limit)

    # ── 3. DB skor zenginleştirme ────────────────────────────────────────
    results = result.get("results", [])
    await _enrich_lead_ids(results, db)
    result["summary"] = _calc_summary(results)

    # ── 4. Cache'e yaz (hata/zaman aşımı yoksa) ─────────────────────────
    result["cache_hit"]    = False
    result["cached_at"]    = datetime.now(timezone.utc).isoformat()
    result["result_count"] = len(results)

    if redis and not result.get("error") and results:
        await redis.set(cache_key, json.dumps(result), ex=CACHE_TTL_SECONDS)
        logger.info("[CACHE WRITE] key=%s ttl=%dd results=%d",
                    cache_key, CACHE_TTL_SECONDS // 86400, len(results))

    return result
