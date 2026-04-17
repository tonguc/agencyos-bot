import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from repositories.proposal import ProposalRepository
from schemas.common import JobResponse
from schemas.proposal import ProposalOut
from services.proposal_service import generate_proposal_for_lead

router = APIRouter(tags=["proposals"])


@router.post("/leads/{lead_id}/proposal", response_model=JobResponse)
async def trigger_proposal(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        proposal = await generate_proposal_for_lead(lead_id, db)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return JobResponse(
        job_id=proposal.id,
        status="completed",
        result=ProposalOut.model_validate(proposal).model_dump(),
    )


@router.get("/leads/{lead_id}/proposal", response_model=ProposalOut)
async def get_proposal(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    proposal = await ProposalRepository(db).get_latest_for_lead(lead_id)
    if not proposal:
        raise HTTPException(404, "Teklif bulunamadi")
    return proposal


@router.get("/proposals/{proposal_id}/pdf")
async def download_pdf(proposal_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    proposal = await ProposalRepository(db).get(proposal_id)
    if not proposal:
        raise HTTPException(404, "Teklif bulunamadi")
    if not proposal.pdf_path or not Path(proposal.pdf_path).exists():
        raise HTTPException(404, "PDF bulunamadi")
    return FileResponse(
        proposal.pdf_path,
        media_type="application/pdf",
        filename=f"teklif-{str(proposal_id)[:8]}.pdf",
    )
