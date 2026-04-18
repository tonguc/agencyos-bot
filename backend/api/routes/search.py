from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.search_service import run_search

router = APIRouter(tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(25, ge=1, le=60)


@router.post("/search")
async def search(body: SearchRequest) -> dict:
    return await run_search(body.query, limit=body.limit)
