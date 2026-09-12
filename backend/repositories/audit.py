import uuid
from datetime import datetime

from sqlalchemy import select

from models.audit import Audit
from repositories.base import BaseRepository


class AuditRepository(BaseRepository[Audit]):
    model = Audit

    async def get_latest_for_lead(
        self,
        lead_id: uuid.UUID,
        since_dt: datetime | None = None,
    ) -> Audit | None:
        """En yeni audit. since_dt verilirse sadece o tarihten sonra olusanlari arar
        (task-level idempotency: ARQ retry sirasinda zaten yazilan audit'i bulmak)."""
        stmt = select(Audit).where(Audit.lead_id == lead_id)
        if since_dt is not None:
            stmt = stmt.where(Audit.created_at >= since_dt)
        stmt = stmt.order_by(Audit.created_at.desc()).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_for_lead(self, lead_id: uuid.UUID) -> list[Audit]:
        result = await self._session.execute(
            select(Audit)
            .where(Audit.lead_id == lead_id)
            .order_by(Audit.created_at.desc())
        )
        return list(result.scalars().all())
