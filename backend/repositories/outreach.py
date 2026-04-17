import uuid

from sqlalchemy import select

from models.outreach import OutreachMessage
from repositories.base import BaseRepository


class OutreachRepository(BaseRepository[OutreachMessage]):
    model = OutreachMessage

    async def get_latest_for_lead(self, lead_id: uuid.UUID) -> OutreachMessage | None:
        result = await self._session.execute(
            select(OutreachMessage)
            .where(OutreachMessage.lead_id == lead_id)
            .order_by(OutreachMessage.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all_for_lead(self, lead_id: uuid.UUID) -> list[OutreachMessage]:
        result = await self._session.execute(
            select(OutreachMessage)
            .where(OutreachMessage.lead_id == lead_id)
            .order_by(OutreachMessage.created_at.desc())
        )
        return list(result.scalars().all())
