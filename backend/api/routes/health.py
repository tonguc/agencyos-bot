import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from database import check_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    db: str
    timestamp: str
    version: str = "0.1.0"


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    db_ok = await check_db()
    status = "ok" if db_ok else "degraded"
    if not db_ok:
        logger.warning("Health check: DB bağlantısı kurulamadı")
    return HealthResponse(
        status=status,
        db="connected" if db_ok else "unreachable",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
