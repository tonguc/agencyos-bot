import logging
import uuid

from database import AsyncSessionFactory
from repositories.job import JobRepository
from services.lead_service import collect_and_save

logger = logging.getLogger(__name__)


async def run_collect_job(
    ctx,
    sector: str,
    city: str,
    district: str,
    limit: int,
    job_id: str,
    query: str = "",
) -> dict:
    job_uuid = uuid.UUID(job_id)

    async with AsyncSessionFactory() as db:
        job = await JobRepository(db).get(job_uuid)
        if job:
            label = query or sector
            await JobRepository(db).mark_running(job, f"{label} / {city} taranıyor...")
            await db.commit()

    try:
        async with AsyncSessionFactory() as db:
            result = await collect_and_save(sector, city, district, limit, db, query=query)
            await db.commit()

        async with AsyncSessionFactory() as db:
            job = await JobRepository(db).get(job_uuid)
            if job:
                await JobRepository(db).mark_completed(job, result)
                await db.commit()

        logger.info("run_collect_job tamamlandi: %s/%s saved=%s", sector, city, result.get("saved"))
        return result

    except Exception as e:
        logger.error("run_collect_job hatasi: %s err=%s", sector, e)
        async with AsyncSessionFactory() as db:
            job = await JobRepository(db).get(job_uuid)
            if job:
                await JobRepository(db).mark_failed(job, str(e))
                await db.commit()
        raise
