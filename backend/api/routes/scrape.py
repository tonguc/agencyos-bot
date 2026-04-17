from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.lead import ScrapeRequest
from schemas.common import JobResponse
from services.lead_service import collect_and_save

router = APIRouter(tags=["scrape"])


@router.post("/scrape", response_model=JobResponse)
async def scrape_leads(body: ScrapeRequest, db: AsyncSession = Depends(get_db)):
    import uuid
    result = await collect_and_save(
        sector=body.sector,
        city=body.city,
        district=body.district,
        limit=body.limit,
        db=db,
    )
    return JobResponse(job_id=uuid.uuid4(), status="completed", result=result)
