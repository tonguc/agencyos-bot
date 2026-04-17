import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from repositories.audit import AuditRepository
from schemas.audit import AuditOut
from schemas.common import JobResponse
from services.audit_service import run_audit

router = APIRouter(prefix="/leads", tags=["audit"])


@router.post("/{lead_id}/audit", response_model=JobResponse)
async def trigger_audit(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        audit = await run_audit(lead_id, db)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return JobResponse(job_id=audit.id, status="completed", result=AuditOut.model_validate(audit).model_dump())


@router.get("/{lead_id}/audit", response_model=AuditOut)
async def get_audit(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    audit = await AuditRepository(db).get_latest_for_lead(lead_id)
    if not audit:
        raise HTTPException(404, "Audit bulunamadi")
    return audit
