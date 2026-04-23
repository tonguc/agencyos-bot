import base64
import uuid
from pathlib import Path

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
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
    repo = JobRepository(db)
    existing = await repo.find_active_for_lead(lead_id, "generate_proposal")
    if existing:
        return JobResponse(job_id=existing.id, status=existing.status, result=None)

    job = await repo.create(
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

    fname = f"teklif-{str(proposal_id)[:8]}.pdf"

    # Yeni yol: PDF bytes DB'de (content._pdf_b64)
    pdf_b64 = (proposal.content or {}).get("_pdf_b64")
    if pdf_b64:
        pdf_bytes = base64.b64decode(pdf_b64)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        )

    # Eski yol: dosya sistemi (geriye dönük uyumluluk)
    if proposal.pdf_path and Path(proposal.pdf_path).exists():
        return FileResponse(proposal.pdf_path, media_type="application/pdf", filename=fname)

    raise HTTPException(404, "PDF bulunamadi — teklifi yeniden olusturun")
