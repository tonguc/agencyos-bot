import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from repositories.job import JobRepository
from schemas.job import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobOut])
async def list_jobs(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = JobRepository(db)
    items = await repo.get_all(limit=limit, offset=offset)
    if status:
        items = [j for j in items if j.status == status]
    return items


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await JobRepository(db).get(job_id)
    if not job:
        raise HTTPException(404, "Job bulunamadi")
    return job
