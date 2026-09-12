import logging
import uuid

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from jobs.pool import get_arq_pool
from repositories.job import JobRepository
from repositories.outreach import OutreachRepository
from schemas.common import JobResponse
from schemas.outreach import MarkSentRequest, OutreachOut
from services.outreach_service import generate_followup, mark_sent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["outreach"])


@router.post("/{lead_id}/outreach", response_model=JobResponse)
async def trigger_outreach(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    arq: ArqRedis = Depends(get_arq_pool),
):
    repo = JobRepository(db)
    existing = await repo.find_active_for_lead(lead_id, "generate_outreach")
    if existing:
        logger.info("trigger_outreach: existing job | lead=%s job=%s",
                    str(lead_id)[:8], str(existing.id)[:8])
        return JobResponse(job_id=existing.id, status=existing.status, result=None)

    job = await repo.create(
        type="generate_outreach",
        payload={"lead_id": str(lead_id)},
    )
    await db.commit()
    await arq.enqueue_job("run_outreach_job", str(lead_id), str(job.id))
    logger.info("trigger_outreach: enqueued | lead=%s job=%s",
                str(lead_id)[:8], str(job.id)[:8])
    return JobResponse(job_id=job.id, status="pending", result=None)


@router.get("/{lead_id}/outreach", response_model=OutreachOut)
async def get_outreach(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    outreach = await OutreachRepository(db).get_latest_for_lead(lead_id)
    if not outreach:
        raise HTTPException(404, "Outreach bulunamadi")
    return outreach


@router.patch("/{lead_id}/outreach/{outreach_id}/send", response_model=OutreachOut)
async def send_outreach(
    lead_id: uuid.UUID,
    outreach_id: uuid.UUID,
    body: MarkSentRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        updated = await mark_sent(outreach_id, body.version, body.channel, db)
    except ValueError as e:
        logger.warning("send_outreach: not found | lead=%s outreach=%s err=%s",
                       str(lead_id)[:8], str(outreach_id)[:8], e)
        raise HTTPException(404, str(e))
    return updated


@router.post("/{lead_id}/followup")
async def get_followup(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        text = await generate_followup(lead_id, db)
    except ValueError as e:
        logger.warning("get_followup: %s | lead=%s", e, str(lead_id)[:8])
        raise HTTPException(404, str(e))
    return {"text": text}
