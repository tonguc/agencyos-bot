import logging
import uuid

from database import AsyncSessionFactory
from repositories.job import JobRepository
from services.outreach_service import generate_outreach

logger = logging.getLogger(__name__)


async def run_outreach_job(ctx, lead_id: str, job_id: str) -> dict:
    lead_uuid = uuid.UUID(lead_id)
    job_uuid = uuid.UUID(job_id)

    job_created_at = None
    async with AsyncSessionFactory() as db:
        job = await JobRepository(db).get(job_uuid)
        if job:
            job_created_at = job.created_at  # idempotency anchor
            await JobRepository(db).mark_running(job, "Mesajlar yazılıyor...")
            await db.commit()

    try:
        async with AsyncSessionFactory() as db:
            outreach = await generate_outreach(lead_uuid, db, since_dt=job_created_at)
            await db.commit()

        result = {"outreach_id": str(outreach.id), "recommended": outreach.recommended}

        async with AsyncSessionFactory() as db:
            job = await JobRepository(db).get(job_uuid)
            if job:
                await JobRepository(db).mark_completed(job, result)
                await db.commit()

        logger.info("run_outreach_job tamamlandi: lead=%s", lead_id[:8])
        return result

    except Exception as e:
        logger.error("run_outreach_job hatasi: lead=%s err=%s", lead_id[:8], e)
        async with AsyncSessionFactory() as db:
            job = await JobRepository(db).get(job_uuid)
            if job:
                await JobRepository(db).mark_failed(job, str(e))
                await db.commit()
        raise
