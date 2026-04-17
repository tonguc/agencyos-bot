"""Shared activity logging utility for all services."""

import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from models.activity_log import ActivityLog

logger = logging.getLogger(__name__)


async def log_event(
    db: AsyncSession,
    event: str,
    data: dict,
    lead_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
) -> None:
    try:
        entry = ActivityLog(lead_id=lead_id, job_id=job_id, event=event, data=data)
        db.add(entry)
        await db.flush()
    except Exception as e:
        logger.warning("activity log yazılamadı: %s", e)
