import uuid

from sqlalchemy import select

from models.audit import Audit
from repositories.base import BaseRepository


class AuditRepository(BaseRepository[Audit]):
    model = Audit

    async def get_latest_for_lead(self, lead_id: uuid.UUID) -> Audit | None:
        result = await self._session.execute(
            select(Audit)
            .where(Audit.lead_id == lead_id)
            .order_by(Audit.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all_for_lead(self, lead_id: uuid.UUID) -> list[Audit]:
        result = await self._session.execute(
            select(Audit)
            .where(Audit.lead_id == lead_id)
            .order_by(Audit.created_at.desc())
        )
        return list(result.scalars().all())
