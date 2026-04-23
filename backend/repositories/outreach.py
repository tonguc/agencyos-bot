import uuid
from datetime import datetime

from sqlalchemy import select

from models.outreach import OutreachMessage
from repositories.base import BaseRepository


class OutreachRepository(BaseRepository[OutreachMessage]):
    model = OutreachMessage

    async def get_latest_for_lead(
        self,
        lead_id: uuid.UUID,
        since_dt: datetime | None = None,
    ) -> OutreachMessage | None:
        """En yeni outreach. since_dt verilirse sadece o tarihten sonra olusanlari
        arar (ARQ retry idempotency)."""
        stmt = select(OutreachMessage).where(OutreachMessage.lead_id == lead_id)
        if since_dt is not None:
            stmt = stmt.where(OutreachMessage.created_at >= since_dt)
        stmt = stmt.order_by(OutreachMessage.created_at.desc()).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_for_lead(self, lead_id: uuid.UUID) -> list[OutreachMessage]:
        result = await self._session.execute(
            select(OutreachMessage)
            .where(OutreachMessage.lead_id == lead_id)
            .order_by(OutreachMessage.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_reply(
        self,
        outreach: OutreachMessage,
        reply_text: str,
        intent: str,
        confidence: float,
    ) -> OutreachMessage:
        outreach.reply_text = reply_text
        outreach.reply_intent = intent
        outreach.reply_confidence = confidence
        await self._session.flush()
        return outreach

    async def update_followup_stage(
        self,
        outreach: OutreachMessage,
        stage: int,
    ) -> OutreachMessage:
        outreach.followup_stage = stage
        await self._session.flush()
        return outreach
