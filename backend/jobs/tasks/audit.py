import asyncio
import logging
import uuid

from database import AsyncSessionFactory
from repositories.job import JobRepository
from services.audit_service import run_audit

logger = logging.getLogger(__name__)


async def run_audit_job(ctx, lead_id: str, job_id: str) -> dict:
    job_uuid = uuid.UUID(job_id)
    try:
        # Leave time to persist errors before ARQ's 240-second timeout.
        async with asyncio.timeout(210):
            lead_uuid = uuid.UUID(lead_id)
            async with AsyncSessionFactory() as db:
                job = await JobRepository(db).get(job_uuid)
                if not job:
                    raise ValueError("Audit job bulunamadı")
                await db.refresh(job, with_for_update=True)
                if job.status in ("completed", "failed"):
                    return job.result or {}
                job_created_at = job.created_at
                await JobRepository(db).mark_running(job, "Audit başlıyor...")
                await db.commit()

            async with AsyncSessionFactory() as db:
                audit = await run_audit(lead_uuid, db, since_dt=job_created_at)
                result = {"audit_id": str(audit.id), "score": audit.general_score}
                job = await JobRepository(db).get(job_uuid)
                if not job:
                    raise ValueError("Audit job bulunamadı")
                # Persist the audit, lead changes and completion atomically.
                await JobRepository(db).mark_completed(job, result)
                await db.commit()
            return result
    except Exception as exc:
        message = ("Audit zaman aşımına uğradı. Tekrar deneyin." if isinstance(exc, TimeoutError)
                   else "Audit tamamlanamadı. Worker ve AI servis yapılandırmasını kontrol edin.")
        logger.error("Audit failed: job=%s error_type=%s", job_id, type(exc).__name__)
        try:
            async with AsyncSessionFactory() as db:
                job = await JobRepository(db).get(job_uuid)
                if job and job.status != "completed":
                    await JobRepository(db).mark_failed(job, message)
                    await db.commit()
        except Exception:
            logger.error("Audit failure status could not be persisted: job=%s", job_id)
        raise
