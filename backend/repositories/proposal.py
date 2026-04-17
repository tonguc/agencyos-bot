import uuid

from sqlalchemy import select

from models.proposal import Proposal
from repositories.base import BaseRepository


class ProposalRepository(BaseRepository[Proposal]):
    model = Proposal

    async def get_latest_for_lead(self, lead_id: uuid.UUID) -> Proposal | None:
        result = await self._session.execute(
            select(Proposal)
            .where(Proposal.lead_id == lead_id)
            .order_by(Proposal.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
