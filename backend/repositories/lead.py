from sqlalchemy import select, func, delete

from models.lead import Lead
from repositories.base import BaseRepository
import uuid

# Valid pipeline statuses in order
PIPELINE_STATUSES = ["Yeni", "Audit", "Mesaj", "Cevap", "Demo", "Teklif", "Kapandi", "Soguk"]


class LeadRepository(BaseRepository[Lead]):
    model = Lead

    async def get_by_status(self, status: str, *, limit: int = 100) -> list[Lead]:
        result = await self._session.execute(
            select(Lead)
            .where(Lead.status == status)
            .order_by(Lead.opportunity_score.desc().nullslast())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_sector(self, sector: str, *, limit: int = 100) -> list[Lead]:
        result = await self._session.execute(
            select(Lead)
            .where(Lead.sector == sector)
            .order_by(Lead.opportunity_score.desc().nullslast())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_hot(self, *, limit: int = 20) -> list[Lead]:
        """High urgency leads not yet converted."""
        result = await self._session.execute(
            select(Lead)
            .where(Lead.status.in_(["Yeni", "Audit", "Mesaj"]))
            .order_by(Lead.opportunity_score.desc().nullslast())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def pipeline_counts(self) -> dict[str, int]:
        result = await self._session.execute(
            select(Lead.status, func.count(Lead.id))
            .group_by(Lead.status)
        )
        counts = {row[0]: row[1] for row in result.all()}
        return {s: counts.get(s, 0) for s in PIPELINE_STATUSES}

    async def filter(
        self,
        *,
        sector: str | None = None,
        city: str | None = None,
        district: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Lead], int]:
        stmt = select(Lead)
        count_stmt = select(func.count(Lead.id))

        if sector:
            stmt = stmt.where(Lead.sector == sector)
            count_stmt = count_stmt.where(Lead.sector == sector)
        if city:
            stmt = stmt.where(Lead.city == city)
            count_stmt = count_stmt.where(Lead.city == city)
        if district:
            stmt = stmt.where(Lead.district == district)
            count_stmt = count_stmt.where(Lead.district == district)
        if status:
            stmt = stmt.where(Lead.status == status)
            count_stmt = count_stmt.where(Lead.status == status)
        if priority:
            stmt = stmt.where(Lead.priority == priority)
            count_stmt = count_stmt.where(Lead.priority == priority)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(Lead.name.ilike(like) | Lead.city.ilike(like))
            count_stmt = count_stmt.where(Lead.name.ilike(like) | Lead.city.ilike(like))

        stmt = stmt.order_by(Lead.opportunity_score.desc().nullslast()).limit(limit).offset(offset)

        total = (await self._session.execute(count_stmt)).scalar_one()
        leads = list((await self._session.execute(stmt)).scalars().all())
        return leads, total

    async def find_by_phones(self, phones: list[str]) -> dict[str, uuid.UUID]:
        """Return {phone: lead_id} for any phone that exists in the DB."""
        if not phones:
            return {}
        result = await self._session.execute(
            select(Lead.phone, Lead.id).where(Lead.phone.in_(phones))
        )
        return {row[0]: row[1] for row in result.all()}

    async def delete_by_sector_city(self, sector: str, city: str = "") -> int:
        stmt = delete(Lead).where(Lead.sector == sector)
        if city:
            stmt = stmt.where(Lead.city == city)
        result = await self._session.execute(stmt)
        return result.rowcount

    async def find_scores_by_phones(self, phones: list[str]) -> dict[str, dict]:
        """Return {phone: {id, opportunity_score, priority, status}} for phones in DB."""
        if not phones:
            return {}
        result = await self._session.execute(
            select(Lead.phone, Lead.id, Lead.opportunity_score, Lead.priority, Lead.status)
            .where(Lead.phone.in_(phones))
        )
        return {
            row[0]: {
                "id":                str(row[1]),
                "opportunity_score": row[2],
                "priority":          row[3],
                "status":            row[4],
            }
            for row in result.all()
        }
