import logging
import uuid

from database import AsyncSessionFactory
from repositories.job import JobRepository
from services.audit_service import run_audit

logger = logging.getLogger(__name__)


async def run_audit_job(ctx, lead_id: str, job_id: str) -> dict:
    lead_uuid = uuid.UUID(lead_id)
    job_uuid = uuid.UUID(job_id)

    job_created_at = None
    async with AsyncSessionFactory() as db:
        job = await JobRepository(db).get(job_uuid)
        if job:
            job_created_at = job.created_at  # idempotency anchor: retry sırasında bu job'un audit'ini tekrar üretme
            await JobRepository(db).mark_running(job, "Audit başlıyor...")
            await db.commit()

    try:
        async with AsyncSessionFactory() as db:
            audit = await run_audit(lead_uuid, db, since_dt=job_created_at)
            await db.commit()

        result = {"audit_id": str(audit.id), "score": audit.general_score}

        async with AsyncSessionFactory() as db:
            job = await JobRepository(db).get(job_uuid)
            if job:
                await JobRepository(db).mark_completed(job, result)
                await db.commit()

        logger.info("run_audit_job tamamlandi: lead=%s score=%s", lead_id[:8], audit.general_score)
        return result

    except Exception as e:
        logger.error("run_audit_job hatasi: lead=%s err=%s", lead_id[:8], e)
        async with AsyncSessionFactory() as db:
            job = await JobRepository(db).get(job_uuid)
            if job:
                await JobRepository(db).mark_failed(job, str(e))
                await db.commit()
        raise
