import logging
import uuid

from database import AsyncSessionFactory
from repositories.job import JobRepository
from services.proposal_service import generate_proposal_for_lead

logger = logging.getLogger(__name__)


async def run_proposal_job(ctx, lead_id: str, job_id: str) -> dict:
    lead_uuid = uuid.UUID(lead_id)
    job_uuid = uuid.UUID(job_id)

    async with AsyncSessionFactory() as db:
        job = await JobRepository(db).get(job_uuid)
        if job:
            await JobRepository(db).mark_running(job, "Teklif hazırlanıyor...")
            await db.commit()

    try:
        async with AsyncSessionFactory() as db:
            proposal = await generate_proposal_for_lead(lead_uuid, db)
            await db.commit()

        result = {"proposal_id": str(proposal.id), "pdf_path": proposal.pdf_path}

        async with AsyncSessionFactory() as db:
            job = await JobRepository(db).get(job_uuid)
            if job:
                await JobRepository(db).mark_completed(job, result)
                await db.commit()

        logger.info("run_proposal_job tamamlandi: lead=%s", lead_id[:8])
        return result

    except Exception as e:
        logger.error("run_proposal_job hatasi: lead=%s err=%s", lead_id[:8], e)
        async with AsyncSessionFactory() as db:
            job = await JobRepository(db).get(job_uuid)
            if job:
                await JobRepository(db).mark_failed(job, str(e))
                await db.commit()
        raise
