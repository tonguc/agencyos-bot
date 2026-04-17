import uuid
from pathlib import Path

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from jobs.pool import get_arq_pool
from repositories.job import JobRepository
from repositories.proposal import ProposalRepository
from schemas.common import JobResponse
from schemas.proposal import ProposalOut

router = APIRouter(tags=["proposals"])


@router.post("/leads/{lead_id}/proposal", response_model=JobResponse)
async def trigger_proposal(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    arq: ArqRedis = Depends(get_arq_pool),
):
    job = await JobRepository(db).create(
        type="generate_proposal",
        payload={"lead_id": str(lead_id)},
    )
    await db.commit()
    await arq.enqueue_job("run_proposal_job", str(lead_id), str(job.id))
    return JobResponse(job_id=job.id, status="pending", result=None)


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
