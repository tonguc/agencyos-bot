import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from database import check_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    db: str
    redis: str
    worker: str
    timestamp: str
    version: str = "0.1.0"


@router.get("/health", response_model=HealthResponse)
async def health(request: Request, response: Response) -> HealthResponse:
    db_ok = await check_db()
    redis_ok = worker_ok = False
    try:
        pool = request.app.state.arq_pool
        redis_ok = bool(await pool.ping())
        worker_ok = bool(await pool.exists("arq:queue:health-check"))
    except Exception:
        pass
    status = "ok" if db_ok and redis_ok and worker_ok else "degraded"
    if status != "ok":
        response.status_code = 503
    if not db_ok:
        logger.warning("Health check: DB bağlantısı kurulamadı")
    return HealthResponse(
        status=status,
        db="connected" if db_ok else "unreachable",
        redis="connected" if redis_ok else "unreachable",
        worker="available" if worker_ok else "unavailable",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
