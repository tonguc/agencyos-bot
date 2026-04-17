import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from repositories.outreach import OutreachRepository
from schemas.common import JobResponse
from schemas.outreach import MarkSentRequest, OutreachOut
from services.outreach_service import generate_followup, generate_outreach, mark_sent

router = APIRouter(prefix="/leads", tags=["outreach"])


@router.post("/{lead_id}/outreach", response_model=JobResponse)
async def trigger_outreach(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        outreach = await generate_outreach(lead_id, db)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return JobResponse(
        job_id=outreach.id,
        status="completed",
        result=OutreachOut.model_validate(outreach).model_dump(),
    )


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
