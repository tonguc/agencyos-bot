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

router = APIRouter(prefix="/leads", tags=["outreach"])


@router.post("/{lead_id}/outreach", response_model=JobResponse)
async def trigger_outreach(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    arq: ArqRedis = Depends(get_arq_pool),
):
    job = await JobRepository(db).create(
        type="generate_outreach",
        payload={"lead_id": str(lead_id)},
    )
    await db.commit()
    await arq.enqueue_job("run_outreach_job", str(lead_id), str(job.id))
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
        raise HTTPException(404, str(e))
    return updated


@router.post("/{lead_id}/followup")
async def get_followup(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        text = await generate_followup(lead_id, db)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"text": text}
