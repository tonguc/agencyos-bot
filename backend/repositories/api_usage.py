from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func

from models.api_usage_log import ApiUsageLog
from repositories.base import BaseRepository


class ApiUsageRepository(BaseRepository[ApiUsageLog]):
    model = ApiUsageLog

    async def daily_spend(self, *, provider: str | None = None) -> dict[str, float]:
        """Son 24 saatlik spend, provider basinda ($ USD).

        provider=None ise tum provider'lar icin {provider: usd} doner.
        provider verilirse {provider: usd} (tek anahtar).
        """
        since = datetime.now(timezone.utc) - timedelta(days=1)
        stmt = (
            select(ApiUsageLog.provider, func.coalesce(func.sum(ApiUsageLog.cost_usd), 0.0))
            .where(ApiUsageLog.created_at >= since)
            .group_by(ApiUsageLog.provider)
        )
        if provider:
            stmt = stmt.where(ApiUsageLog.provider == provider)
        result = await self._session.execute(stmt)
        return {row[0]: float(row[1]) for row in result.all()}
