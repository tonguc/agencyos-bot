import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.lead import Lead
from repositories.lead import LeadRepository
from schemas.lead import LeadCreate, LeadListOut, LeadOut, LeadUpdate, PipelineOut
from services.lead_service import update_status

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=LeadListOut)
async def list_leads(
    sector: str | None = Query(None),
    city: str | None = Query(None),
    district: str | None = Query(None),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(20, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = LeadRepository(db)
    items, total = await repo.filter(
        sector=sector, city=city, district=district,
        status=status, priority=priority,
        search=search, limit=limit, offset=offset,
    )
    return LeadListOut(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=LeadOut, status_code=201)
async def create_lead(body: LeadCreate, db: AsyncSession = Depends(get_db)):
    repo = LeadRepository(db)
    lead = await repo.create(**body.model_dump())
    return lead


@router.get("/pipeline", response_model=PipelineOut)
async def pipeline_counts(db: AsyncSession = Depends(get_db)):
    repo = LeadRepository(db)
    counts, score_tiers = await asyncio.gather(
        repo.pipeline_counts(),
        repo.score_distribution(),
    )
    return PipelineOut(counts=counts, score_tiers=score_tiers)


@router.get("/{lead_id}", response_model=LeadOut)
async def get_lead(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    lead = await LeadRepository(db).get(lead_id)
    if not lead:
        raise HTTPException(404, "Lead bulunamadi")
    return lead


@router.patch("/{lead_id}", response_model=LeadOut)
async def update_lead(
    lead_id: uuid.UUID, body: LeadUpdate, db: AsyncSession = Depends(get_db)
):
    repo = LeadRepository(db)
    lead = await repo.get(lead_id)
    if not lead:
        raise HTTPException(404, "Lead bulunamadi")
    updated = await repo.update(lead, **{k: v for k, v in body.model_dump().items() if v is not None})
    return updated


@router.delete("/bulk/sector", status_code=200)
async def delete_leads_by_sector(
    sector: str = Query(...),
    city: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Bir sektörün (ve opsiyonel şehrin) tüm lead'lerini siler."""
    deleted = await LeadRepository(db).delete_by_sector_city(sector, city or "")
    await db.commit()
    return {"deleted": deleted}


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    # Use SQL-level delete so SQLAlchemy doesn't attempt async lazy-load of
    # relationships (audits, outreach, etc.) — DB ON DELETE CASCADE handles children.
    result = await db.execute(sql_delete(Lead).where(Lead.id == lead_id))
    if result.rowcount == 0:
        raise HTTPException(404, "Lead bulunamadi")
