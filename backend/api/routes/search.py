import hashlib
import json

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from repositories.lead import LeadRepository
from services.search_service import run_search

router = APIRouter(tags=["search"])

_PRIORITY_TO_SEGMENT = {
    "yuksek": "hot",
    "orta":   "warm",
    "dusuk":  "low",
}

SEARCH_CACHE_TTL = 3600  # 1 hour


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(25, ge=1, le=60)


def _cache_key(query: str, limit: int) -> str:
    raw = f"{query.strip().lower()}:{limit}"
    return "search:" + hashlib.md5(raw.encode()).hexdigest()


@router.post("/search")
async def search(body: SearchRequest, request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    cache_key = _cache_key(body.query, body.limit)

    # Try Redis cache first
    redis = getattr(request.app.state, "arq_pool", None)
    if redis:
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)

    result = await run_search(body.query, limit=body.limit)

    phones = [r["phone"] for r in result.get("results", []) if r.get("phone")]
    if phones:
        db_scores = await LeadRepository(db).find_scores_by_phones(phones)
    else:
        db_scores = {}

    for r in result.get("results", []):
        phone = r.get("phone") or ""
        db_entry = db_scores.get(phone)
        if not db_entry:
            r["lead_id"] = None
            continue
        r["lead_id"] = db_entry["id"]
        if db_entry["status"] != "Yeni" and db_entry["opportunity_score"] is not None:
            r["score"]    = db_entry["opportunity_score"]
            r["priority"] = db_entry["priority"]
            r["segment"]  = _PRIORITY_TO_SEGMENT.get(db_entry["priority"] or "", r["segment"])

    results = result.get("results", [])
    result["summary"] = {
        "hot":    sum(1 for r in results if r["segment"] == "hot"),
        "warm":   sum(1 for r in results if r["segment"] == "warm"),
        "ok":     sum(1 for r in results if r["segment"] == "ok"),
        "low":    sum(1 for r in results if r["segment"] == "low"),
        "review": sum(1 for r in results if r["segment"] == "review"),
        "total":  len(results),
    }

    # Cache successful results (not errors/timeouts)
    if redis and not result.get("error") and results:
        await redis.set(cache_key, json.dumps(result), ex=SEARCH_CACHE_TTL)

    return result
