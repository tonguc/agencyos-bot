from datetime import datetime, timezone

from sqlalchemy import select

from models.job import Job
from repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    model = Job

    async def get_recent(self, *, limit: int = 20) -> list[Job]:
        result = await self._session.execute(
            select(Job).order_by(Job.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def mark_running(self, job: Job, message: str = "") -> Job:
        return await self.update(
            job,
            status="running",
            started_at=datetime.now(timezone.utc),
            progress_pct=0,
            progress_message=message,
        )

    async def mark_progress(self, job: Job, pct: int, message: str = "") -> Job:
        return await self.update(job, progress_pct=pct, progress_message=message)

    async def mark_completed(self, job: Job, result: dict) -> Job:
        return await self.update(
            job,
            status="completed",
            progress_pct=100,
            result=result,
            finished_at=datetime.now(timezone.utc),
        )

    async def mark_failed(self, job: Job, error: str) -> Job:
        return await self.update(
            job,
            status="failed",
            error_message=error,
            finished_at=datetime.now(timezone.utc),
        )
