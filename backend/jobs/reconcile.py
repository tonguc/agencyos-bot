"""Recover terminal queue failures for audits using stable ARQ IDs.

Legacy jobs have unrelated queue IDs and are deliberately excluded.
Never re-enqueue work or infer failure while ARQ still owns a live job.
"""
from datetime import datetime, timedelta, timezone

from arq.jobs import Job as QueueJob, JobStatus
from sqlalchemy import select

from database import AsyncSessionFactory
from models.job import Job
from repositories.job import JobRepository


async def reconcile_audits(ctx):
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    async with AsyncSessionFactory() as db:
        jobs = (await db.execute(select(Job).where(
            Job.type == "generate_audit",
            Job.status.in_(["pending", "running"]),
            Job.created_at < cutoff,
            Job.payload["queue_tracking"].as_boolean().is_(True),
        ).order_by(Job.created_at).limit(100))).scalars().all()
        for job in jobs:
            queued = QueueJob(str(job.id), redis=ctx["redis"])
            status = await queued.status()
            if status not in (JobStatus.not_found, JobStatus.complete):
                continue
            # Re-read under a row lock so a concurrent completion is not overwritten.
            await db.refresh(job, with_for_update=True)
            if job.status not in ("pending", "running"):
                continue
            await JobRepository(db).mark_failed(
                job, "Audit kuyrukta sonlandı veya kayboldu. Servis durumunu kontrol edip tekrar deneyin.",
            )
        await db.commit()
