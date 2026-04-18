import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionFactory, get_db
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
    items = await JobRepository(db).get_all(limit=limit, offset=offset)
    if status:
        items = [j for j in items if j.status == status]
    return items


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await JobRepository(db).get(job_id)
    if not job:
        raise HTTPException(404, "Job bulunamadi")
    return job


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await JobRepository(db).get(job_id)
    if not job:
        raise HTTPException(404, "Job bulunamadi")
    await JobRepository(db).delete(job)
    await db.commit()


@router.get("/{job_id}/stream")
async def stream_job(job_id: uuid.UUID):
    """SSE endpoint — streams job status until completed or failed."""

    async def event_generator():
        while True:
            async with AsyncSessionFactory() as db:
                job = await JobRepository(db).get(job_id)

            if job is None:
                yield f"data: {json.dumps({'error': 'not_found'})}\n\n"
                break

            payload = {
                "job_id": str(job.id),
                "status": job.status,
                "progress_pct": job.progress_pct,
                "progress_message": job.progress_message,
                "error_message": job.error_message,
                "result": job.result,
            }
            yield f"data: {json.dumps(payload)}\n\n"

            if job.status in ("completed", "failed"):
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
