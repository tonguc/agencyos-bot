from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from repositories.lead import LeadRepository
from services.search_service import run_search

router = APIRouter(tags=["search"])

# Maps stored priority → search segment
_PRIORITY_TO_SEGMENT = {
    "yuksek": "hot",
    "orta":   "warm",
    "dusuk":  "low",
}


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(25, ge=1, le=60)


@router.post("/search")
async def search(body: SearchRequest, db: AsyncSession = Depends(get_db)) -> dict:
    result = await run_search(body.query, limit=body.limit)

    phones = [r["phone"] for r in result.get("results", []) if r.get("phone")]
    if phones:
        db_scores = await LeadRepository(db).find_scores_by_phones(phones)
    else:
        db_scores = {}

    for r in result.get("results", []):
        phone = r.get("phone") or ""
        db = db_scores.get(phone)
        if not db:
            r["lead_id"] = None
            continue

        r["lead_id"] = db["id"]

        # Eğer lead daha önce audit geçmişse (status != Yeni), DB skorunu kullan.
        # Maps-only sıfırdan puanlama yerine audit'li gerçek skor gösterilir.
        if db["status"] != "Yeni" and db["opportunity_score"] is not None:
            r["score"]    = db["opportunity_score"]
            r["priority"] = db["priority"]
            r["segment"]  = _PRIORITY_TO_SEGMENT.get(db["priority"] or "", r["segment"])

    # Summary'yi güncellenmiş segmentlere göre yeniden hesapla
    results = result.get("results", [])
    result["summary"] = {
        "hot":    sum(1 for r in results if r["segment"] == "hot"),
        "warm":   sum(1 for r in results if r["segment"] == "warm"),
        "ok":     sum(1 for r in results if r["segment"] == "ok"),
        "low":    sum(1 for r in results if r["segment"] == "low"),
        "review": sum(1 for r in results if r["segment"] == "review"),
        "total":  len(results),
    }

    return result
