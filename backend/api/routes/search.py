from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from repositories.lead import LeadRepository
from services.search_service import run_search

router = APIRouter(tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(25, ge=1, le=60)


@router.post("/search")
async def search(body: SearchRequest, db: AsyncSession = Depends(get_db)) -> dict:
    result = await run_search(body.query, limit=body.limit)

    # Try to match results against DB leads by phone number.
    phones = [r["phone"] for r in result.get("results", []) if r.get("phone")]
    phone_to_id: dict[str, str] = {}
    if phones:
        mapping = await LeadRepository(db).find_by_phones(phones)
        phone_to_id = {k: str(v) for k, v in mapping.items()}

    for r in result.get("results", []):
        r["lead_id"] = phone_to_id.get(r.get("phone") or "") or None

    return result
