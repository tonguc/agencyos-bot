import uuid

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from jobs.pool import get_arq_pool
from repositories.audit import AuditRepository
from repositories.job import JobRepository
from schemas.audit import AuditOut
from schemas.common import JobResponse

router = APIRouter(prefix="/leads", tags=["audit"])


@router.post("/{lead_id}/audit", response_model=JobResponse)
async def trigger_audit(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    arq: ArqRedis = Depends(get_arq_pool),
):
    job = await JobRepository(db).create(
        type="generate_audit",
        payload={"lead_id": str(lead_id)},
    )
    await db.commit()
    await arq.enqueue_job("run_audit_job", str(lead_id), str(job.id))
    return JobResponse(job_id=job.id, status="pending", result=None)


@router.get("/{lead_id}/audit", response_model=AuditOut)
async def get_audit(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    audit = await AuditRepository(db).get_latest_for_lead(lead_id)
    if not audit:
        raise HTTPException(404, "Audit bulunamadi")
    return audit
