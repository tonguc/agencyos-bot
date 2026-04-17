from arq import ArqRedis
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from jobs.pool import get_arq_pool
from repositories.job import JobRepository
from schemas.common import JobResponse
from schemas.lead import ScrapeRequest

router = APIRouter(tags=["scrape"])


@router.post("/scrape", response_model=JobResponse)
async def scrape_leads(
    body: ScrapeRequest,
    db: AsyncSession = Depends(get_db),
    arq: ArqRedis = Depends(get_arq_pool),
):
    job = await JobRepository(db).create(
        type="collect_leads",
        payload={
            "sector": body.sector,
            "city": body.city,
            "district": body.district,
            "limit": body.limit,
        },
    )
    await db.commit()
    await arq.enqueue_job(
        "run_collect_job",
        body.sector, body.city, body.district, body.limit,
        str(job.id),
    )
    return JobResponse(job_id=job.id, status="pending", result=None)
