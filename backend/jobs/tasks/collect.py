import asyncio
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

    # Phase 1 — scrape + save. A failure here means nothing was persisted
    # (db.commit runs only on success), so it's safe to mark the job failed.
    try:
        async with AsyncSessionFactory() as db:
            result = await collect_and_save(sector, city, district, limit, db, query=query)
            await db.commit()
    except Exception as e:
        logger.error("run_collect_job scrape hatasi: %s err=%s", sector, e)
        async with AsyncSessionFactory() as db:
            job = await JobRepository(db).get(job_uuid)
            if job:
                await JobRepository(db).mark_failed(job, str(e))
                await db.commit()
        raise

    # Phase 2 — leads are already in the DB. From here on, never mark the job
    # as failed: that would desync job.status from the rows the user can see.
    # Shield from ARQ cancellation so a timeout firing right now can't leave
    # the job stuck in "running" with visible leads.
    async def _mark_completed() -> None:
        async with AsyncSessionFactory() as db:
            job = await JobRepository(db).get(job_uuid)
            if job:
                await JobRepository(db).mark_completed(job, result)
                await db.commit()

    try:
        await asyncio.shield(_mark_completed())
    except asyncio.CancelledError:
        logger.warning(
            "run_collect_job: cancelled after save (saved=%s); mark_completed still finishing in background",
            result.get("saved"),
        )
        raise
    except Exception:
        logger.exception(
            "run_collect_job: leads saved (%s) ama mark_completed duştu — job running'de kalabilir",
            result.get("saved"),
        )

    logger.info("run_collect_job tamamlandi: %s/%s saved=%s", sector, city, result.get("saved"))
    return result
