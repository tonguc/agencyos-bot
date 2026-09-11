import uuid

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from database import get_db
from jobs.pool import get_arq_pool
from repositories.audit import AuditRepository
from repositories.job import JobRepository
from repositories.lead import LeadRepository
from schemas.audit import AuditOut
from schemas.common import JobResponse
from core.sales_output_generator import generate_sales_output
from core.playbook import load_playbook_for_sector
from services.lead_service import lead_to_core_dict

router = APIRouter(prefix="/leads", tags=["audit"])


@router.post("/{lead_id}/audit", response_model=JobResponse)
async def trigger_audit(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    arq: ArqRedis = Depends(get_arq_pool),
):
    if not await LeadRepository(db).get(lead_id):
        raise HTTPException(404, "Lead bulunamadi")
    try:
        worker_alive = await arq.exists("arq:queue:health-check")
    except Exception:
        raise HTTPException(503, "Audit kuyruğuna ulaşılamıyor") from None
    if not worker_alive:
        raise HTTPException(503, "Audit worker çalışmıyor. Servis durumunu kontrol edin.")
    job = await JobRepository(db).create(
        type="generate_audit",
        payload={"lead_id": str(lead_id), "queue_tracking": True},
    )
    await db.commit()
    try:
        queued = await arq.enqueue_job(
            "run_audit_job", str(lead_id), str(job.id), _job_id=str(job.id),
        )
        if queued is None:
            raise RuntimeError("Job kuyruğa eklenemedi")
    except Exception:
        # A lost Redis acknowledgement can occur after the worker has started.
        await db.refresh(job, with_for_update=True)
        if job.status in ("running", "completed"):
            return JobResponse(job_id=job.id, status=job.status, result=job.result)
        await JobRepository(db).mark_failed(job, "Audit kuyruğa eklenemedi. Tekrar deneyin.")
        await db.commit()
        raise HTTPException(503, "Audit kuyruğa eklenemedi") from None
    return JobResponse(job_id=job.id, status="pending", result=None)


@router.get("/{lead_id}/audit", response_model=AuditOut)
async def get_audit(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    audit = await AuditRepository(db).get_latest_for_lead(lead_id)
    if not audit:
        raise HTTPException(404, "Audit bulunamadi")
    return audit


@router.post("/{lead_id}/sales-output")
async def refresh_sales_output(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Mevcut audit verisini kullanarak sadece satış mesajını yeniden üretir."""
    lead = await LeadRepository(db).get(lead_id)
    if not lead:
        raise HTTPException(404, "Lead bulunamadi")

    audit = await AuditRepository(db).get_latest_for_lead(lead_id)
    if not audit or not audit.result:
        raise HTTPException(404, "Önce audit çalıştırılmalı")

    playbook = load_playbook_for_sector(lead.sector or "klinik")
    lead_dict = lead_to_core_dict(lead)
    audit_result = dict(audit.result)

    sales_output = await generate_sales_output(lead_dict, audit_result, playbook)

    new_result = dict(audit.result)
    new_result["sales_output"] = sales_output
    audit.result = new_result
    flag_modified(audit, "result")
    await db.commit()

    return {"sales_output": sales_output}
