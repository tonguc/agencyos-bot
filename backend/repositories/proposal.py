import uuid
from datetime import datetime

from sqlalchemy import select

from models.proposal import Proposal
from repositories.base import BaseRepository


class ProposalRepository(BaseRepository[Proposal]):
    model = Proposal

    async def get_latest_for_lead(
        self,
        lead_id: uuid.UUID,
        since_dt: datetime | None = None,
    ) -> Proposal | None:
        """En yeni proposal. since_dt verilirse sadece o tarihten sonra olusanlari
        arar (ARQ retry idempotency)."""
        stmt = select(Proposal).where(Proposal.lead_id == lead_id)
        if since_dt is not None:
            stmt = stmt.where(Proposal.created_at >= since_dt)
        stmt = stmt.order_by(Proposal.created_at.desc()).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
